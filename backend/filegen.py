import io
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

MAX_THREAD_WORKERS = 3
# Thread-local storage to hold per-thread browser instances safely
_thread_local = threading.local()

def get_thread_browser():
    # basically check if thread has a browser instance, if not then start one
    if not hasattr(_thread_local, "browser") or _thread_local.browser is None: 
        _thread_local.playwright = sync_playwright().start() # if no browser, sure start one up
        _thread_local.browser = _thread_local.playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
    return _thread_local.browser # else return the browser it has

def generate_single_student_pdf(item):
    """Worker function that runs across multiple worker threads in parallel."""
    student_id, test_results = item
    file_content = generate_html(student_id, test_results)
    
    # Each thread fetches its own cached browser instance
    browser = get_thread_browser()
    page = browser.new_page()
    page.set_content(file_content)
    pdf_bytes = page.pdf(
        format="A4",
        print_background=True,
        margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
    )
    page.close()
    
    raw_name = test_results.get('name', 'Student')
    safe_name = raw_name.replace(' ', '_').replace('/', '_')
    safe_id = str(student_id).replace(' ', '_').replace('/', '_')
    filename = f"{safe_name}_{safe_id}_review.pdf"
    
    return filename, pdf_bytes

def generate_html(student_id: str, test_results: dict) -> str:
    name = test_results.get("name", "Student")
    if name == "Name Missing":
        name = f"Student ({student_id})"

    score = test_results.get("score", "N/A")
    topics = test_results.get("topics_to_review", [])

    if topics:
        topics_html = "".join([f'<li class="topic-item">{topic}</li>' for topic in topics])
    else:
        topics_html = '<li class="no-topics">Great job! No topics require review at this time.</li>'

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: #1f2937;
                background-color: #ffffff;
                padding: 24px;
                line-height: 1.5;
            }}
            .header {{
                border-bottom: 3px solid #2563eb;
                padding-bottom: 16px;
                margin-bottom: 24px;
            }}
            .header h1 {{ font-size: 24px; color: #1e3a8a; margin-bottom: 4px; }}
            .header p {{ font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }}
            .student-card {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 28px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .info-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; margin-bottom: 2px; }}
            .info-value {{ font-size: 18px; font-weight: 600; color: #0f172a; }}
            .score-badge {{
                background-color: #dbeafe;
                color: #1e40af;
                font-size: 20px;
                font-weight: 700;
                padding: 6px 16px;
                border-radius: 20px;
            }}
            .section-title {{
                font-size: 16px;
                font-weight: 600;
                color: #334155;
                margin-bottom: 12px;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 6px;
            }}
            .topics-list {{ list-style: none; padding-left: 0; }}
            .topic-item {{
                font-size: 14px;
                color: #334155;
                padding: 10px 12px;
                margin-bottom: 8px;
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-left: 4px solid #2563eb;
                border-radius: 4px;
            }}
            .no-topics {{
                font-size: 14px;
                color: #166534;
                background-color: #f0fdf4;
                border: 1px solid #bbf7d0;
                padding: 12px;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 40px;
                border-top: 1px solid #f1f5f9;
                padding-top: 12px;
                font-size: 11px;
                color: #94a3b8;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Chemistry Assessment Review</h1>
            <p>Mt. SAC Chemistry Workbook Tool</p>
        </div>

        <div class="student-card">
            <div>
                <div class="info-label">Student Name</div>
                <div class="info-value">{name}</div>
                <div class="info-label" style="margin-top: 8px;">Student ID</div>
                <div class="info-value" style="font-size: 14px; font-weight: normal; color: #475569;">{student_id}</div>
            </div>
            <div>
                <div class="info-label" style="margin-bottom: 6px; text-align: right;">Score</div>
                <div class="score-badge">{score}</div>
            </div>
        </div>

        <div class="section-title">Recommended Topics for Review</div>
        <ul class="topics-list">
            {topics_html}
        </ul>

        <div class="footer">
            Generated automatically by Mt. SAC Chemistry Workbook Tool
        </div>
    </body>
    </html>
    """

def file_generator_sync(results, filename):
    # multithread!
    zip_buffer = io.BytesIO()

    with ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS) as executor:
        pdf_results = list(executor.map(generate_single_student_pdf, results.items()))
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for fname, pdf_bytes in pdf_results:
            zip_file.writestr(fname, pdf_bytes)
            
    zip_buffer.seek(0)
    return zip_buffer