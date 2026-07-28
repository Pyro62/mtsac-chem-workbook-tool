import io
import zipfile
import asyncio
from playwright.sync_api import sync_playwright

def generate_pdf_sync(html_content: str) -> bytes: 
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"}
        )
        browser.close()
        return pdf_bytes

async def pdf_generator(html_content: str) -> bytes:
    # Run the sync function in a background thread so it doesn't block FastAPI
    return await asyncio.to_thread(generate_pdf_sync, html_content)

async def file_generator(results, filename):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for student_id, test_results in results.items(): # student id is id, test result is a dict
            file_content = generate_html(student_id,test_results)
            pdf_content = await pdf_generator(file_content)
            
            studentfilename = f"{test_results['name'].replace(' ', '_')}_{student_id}_review.pdf"
            zip_file.writestr(studentfilename, pdf_content)
            
    zip_buffer.seek(0)
    return zip_buffer

def generate_html(student_id: str, test_results: dict)-> str:
    name = test_results.get("name", "Student")
    if name == "Name Missing":
        name = f"Student ({student_id})"

    score = test_results.get("score", "N/A")
    topics = test_results.get("topics_to_review", [])

    # Format review topics as HTML list items
    if topics:
        topics_html = "".join([f'<li class="topic-item"><span class="bullet"></span>{topic}</li>' for topic in topics])
    else:
        topics_html = '<li class="no-topics">Great job! No topics require review at this time.</li>'

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
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
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
            }}
            .header-title h1 {{
                font-size: 24px;
                color: #1e3a8a;
                margin-bottom: 4px;
            }}
            .header-title p {{
                font-size: 13px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .student-card {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 28px;
            }}
            .student-info {{
                display: table;
                width: 100%;
            }}
            .info-col {{
                display: table-cell;
                vertical-align: middle;
            }}
            .info-label {{
                font-size: 11px;
                text-transform: uppercase;
                color: #64748b;
                letter-spacing: 0.5px;
                margin-bottom: 2px;
            }}
            .info-value {{
                font-size: 18px;
                font-weight: 600;
                color: #0f172a;
            }}
            .score-badge {{
                display: inline-block;
                background-color: #dbeafe;
                color: #1e40af;
                font-size: 20px;
                font-weight: 700;
                padding: 6px 16px;
                border-radius: 20px;
                float: right;
            }}
            .section-title {{
                font-size: 16px;
                font-weight: 600;
                color: #334155;
                margin-bottom: 12px;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 6px;
            }}
            .topics-list {{
                list-style: none;
                padding-left: 0;
            }}
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
            <div class="header-title">
                <h1>Chemistry Assessment Review</h1>
                <p>Mt. SAC Chemistry Workbook Tool</p>
            </div>
        </div>

        <div class="student-card">
            <div class="student-info">
                <div class="info-col">
                    <div class="info-label">Student Name</div>
                    <div class="info-value">{name}</div>
                    <div class="info-label" style="margin-top: 8px;">Student ID</div>
                    <div class="info-value" style="font-size: 14px; font-weight: normal; color: #475569;">{student_id}</div>
                </div>
                <div class="info-col" style="text-align: right;">
                    <div class="info-label" style="margin-bottom: 6px;">Score</div>
                    <div class="score-badge">{score}</div>
                </div>
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
    return