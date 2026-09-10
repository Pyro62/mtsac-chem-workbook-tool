import io
import gc
import zipfile
from playwright.sync_api import sync_playwright
from processing import TOPIC_MAP
import base64
import urllib.request
from pypdf import PdfWriter, PdfReader, PageObject
MASCOT_IMAGE_URL = "https://i.ibb.co/spH9N6XS/assessment-image.png"

def get_image_base64(url_or_path: str) -> str:
    """Fetch image from local path or web URL and convert to Base64 URI."""
    try:
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            req = urllib.request.Request(url_or_path, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                img_data = response.read()
        else:
            with open(url_or_path, "rb") as f:
                img_data = f.read()
        
        encoded = base64.b64encode(img_data).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"Warning: Could not load image {url_or_path}: {e}")
        return ""

def generate_html(student_id: str, test_results: dict, image_src: str) -> str:
    name = test_results.get("name", "Student")
    if name == "Name Missing":
        name = f"Student ({student_id})"

    score = test_results.get("score", "N/A")
    topics = test_results.get("topics_to_review", [])

    mascot_html = f'<img src="{image_src}" class="mascot-img" alt="Mascot" />'

    if topics:
        # Convert topic codes (e.g. "2.3") into full titles using TOPIC_MAP
        sections_html = "".join([
            f'<li class="section-item">{TOPIC_MAP.get(code, code)}</li>'
            for code in topics
        ])
    else:
        sections_html = '<li class="no-sections">No specific sections needed — you\'re all caught up!</li>'

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
                padding: 48px 56px;
                line-height: 1.6;
                font-size: 14px;
            }}
            p {{ margin-bottom: 16px; }}
            .highlight {{
                background-color: #fff9a8;
                font-weight: 600;
            }}
            .resource-list {{
                list-style: none;
                padding-left: 0;
                margin-bottom: 16px;
            }}
            .resource-list li {{
                padding-left: 24px;
                position: relative;
                margin-bottom: 6px;
            }}
            .resource-list li .num {{
                position: absolute;
                left: 0;
                font-weight: 600;
            }}
            .encouragement {{
                margin-bottom: 24px;
            }}
            .recommend-block {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 24px;
                margin-bottom: 8px;
            }}
            .recommend-text {{ flex: 1; }}
            .mascot-placeholder {{
                width: 100px;
                height: 100px;
                border: 1px dashed #cbd5e1;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                color: #94a3b8;
                text-align: center;
                flex-shrink: 0;
            }}
            .sections-box {{
                text-align: left;
                margin: 20px 0 28px;
            }}
            .section-item {{
                display: block;
                font-weight: 400;
                font-size: 15px;
                margin-bottom: 6px;
                max-width: 100%;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            .no-sections {{
                display: block;
                font-weight: 600;
                color: #166534;
            }}
            .signoff {{
                font-weight: 700;
                margin-bottom: 4px;
            }}
            .mascot-img {{
                width: 100px;
                height: 100px;
                object-fit: contain;
                flex-shrink: 0;
            }}
        </style>
    </head>
    <body>
        <p>Dear {name} | Score: {score},</p>

        <p>
            Thank you for taking your time to complete the pre-assessment for the Foundations for
            Success in Chemistry Workbook.
            <span class="highlight">Your results are meant to help you identify the math
            subjects that you'll want to review in preparation for your chemistry class.</span>
        </p>

        <p>The workbook has a variety of resources for you, including:</p>
        <ul class="resource-list">
            <li><span class="num">1)</span>Suggestions for time management</li>
            <li><span class="num">2)</span>A passport to encourage you to find support centers on campus</li>
            <li><span class="num">3)</span>A bingo sheet to help you track your progress (you get a prize for completing it!)</li>
            <li><span class="num">4)</span>Plenty of practice problems for the math skills needed in chemistry</li>
        </ul>

        <p class="encouragement">We encourage you to take advantage of the many support resources available at Mt SAC!</p>

        <div class="recommend-block">
            <div class="recommend-text">
                <p>Based on your pre-assessment results, we recommend that you work through the following sections in the workbook:</p>
            </div>
            {mascot_html}
        </div>

        <div class="sections-box">
            {sections_html}
        </div>

        <p class="signoff">Remember, you can do this!</p>
        <p>&mdash; The Chemistry Department Professors</p>
    </body>
    </html>
    """

def file_generator_sync(
    results: dict, 
    filename: str, 
    class_data: dict, 
    concatenate_files: bool = False, 
    print_ready: bool = False
):
    zip_buffer = io.BytesIO()

    mascot_b64 = get_image_base64(MASCOT_IMAGE_URL)

    # 1. Calculate class statistics
    total_students = len(results)
    class_html = generate_class_report_html(class_data, total_students)

    # Determine if merging is required
    should_merge = concatenate_files or print_ready
    merger = PdfWriter() if should_merge else None

    # Helper function to append and insert blank pages if print_ready is enabled
    def append_to_merger(pdf_bytes: bytes):
        if not merger:
            return
        
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)
        
        # Append each page from the current PDF into the merger individualy
        for page in reader.pages:
            merger.add_page(page)

        # If print-ready is requested, ensure even page count per document for duplex printing
        if print_ready:
            page_count = len(reader.pages)
            if page_count % 2 != 0:
                last_page = reader.pages[-1]
                width = float(last_page.mediabox.width)
                height = float(last_page.mediabox.height)
            
                # Create a blank page using the dimensions of the document
                blank_page = PageObject.create_blank_page(width=width, height=height)
                merger.add_page(blank_page)
    
    # 2. Launch a temporary, ultra-lean single Chromium process
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--disable-extensions",
                "--disable-component-update",
                "--disable-background-networking",
                "--disable-sync",
                "--metrics-recording-only",
                "--disable-default-apps",
                "--no-first-run",
                "--mute-audio"
            ]
        )
        page = browser.new_page()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # --- Render Class Summary First ---
            page.set_content(class_html, wait_until="networkidle")
            summary_pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                scale=0.88,
                margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
            )
            if not merger: 
                zip_file.writestr("00_Class_Summary_Report.pdf", summary_pdf_bytes)

            # Append to master PDF merger if enabled
            append_to_merger(summary_pdf_bytes)
            del summary_pdf_bytes  # Immediately free variable memory

            # --- Render Each Student Sequentially ---
            for student_id, test_results in results.items():
                html = generate_html(student_id, test_results, image_src=mascot_b64)

                page.set_content(html, wait_until="networkidle")
                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    scale=0.93,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
                )

                # Append to master PDF merger if enabled
                append_to_merger(pdf_bytes)

                # Format filename
                raw_name = test_results.get('name', 'Student')
                safe_name = raw_name.replace(' ', '_').replace('/', '_')
                safe_id = str(student_id).replace(' ', '_').replace('/', '_')
                fname = f"{safe_name}_{safe_id}_review.pdf"

                # Write directly to ZIP buffer and wipe bytes from Python RAM
                if not merger:
                    zip_file.writestr(fname, pdf_bytes)
                del pdf_bytes

                # Force Python to release unreferenced byte objects immediately
                gc.collect()

            # --- Write Concatenated Master PDF if requested ---
            if merger:
                merged_pdf_buffer = io.BytesIO()
                merger.write(merged_pdf_buffer)
                merger.close()

                merged_filename = "00_Print_Ready_Merged.pdf" if print_ready else "00_All_Students_Merged.pdf"
                zip_file.writestr(merged_filename, merged_pdf_buffer.getvalue())

        # Cleanly close page and browser, releasing ~150MB of C++ RAM back to host OS
        page.close()
        browser.close()

    zip_buffer.seek(0)
    return zip_buffer

def generate_class_report_html(class_data: dict, total_students: int) -> str:
    class_average = class_data.get("average", 0.0)
    missed_topics = class_data.get("missed_topics", [])

    # Calculate highest count to scale the progress bar widths (avoid division by zero)
    max_missed = max([count for _, count in missed_topics], default=1)
    if max_missed == 0:
        max_missed = 1

    # Render Top 3 Focus Cards
    top_3 = missed_topics[:3]
    top_3_html = ""
    for topic_code, count in top_3:
        if count > 0:
            topic_title = TOPIC_MAP.get(topic_code, f"Topic {topic_code}")
            top_3_html += f"""
            <div class="focus-card">
                <span class="focus-badge">{topic_code}</span>
                <div class="focus-info">
                    <div class="focus-title">{topic_title}</div>
                    <div class="focus-count">{count} students struggle with this</div>
                </div>
            </div>
            """

    if not top_3_html:
        top_3_html = '<div class="no-focus">Great job! No topics were missed by students.</div>'

    # Render Progress Bar Chart Rows
    chart_rows_html = ""
    for topic_code, count in missed_topics:
        topic_title = TOPIC_MAP.get(topic_code, f"Topic {topic_code}")
        # Percentage of max count for visual bar fill
        bar_width = int((count / max_missed) * 100)

        # Color coding: red for high missed count, blue for moderate, light grey for zero
        if count == 0:
            bar_class = "bar-zero"
        elif count >= (max_missed * 0.7):
            bar_class = "bar-high"
        else:
            bar_class = "bar-med"

        chart_rows_html += f"""
        <div class="chart-row">
            <div class="topic-label">
                <span class="topic-code">{topic_code}</span>
                <span class="topic-name">{topic_title}</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill {bar_class}" style="width: {bar_width}%;"></div>
            </div>
            <div class="count-badge">{count}</div>
        </div>
        """

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

            .stats-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                margin-bottom: 24px;
            }}
            .stat-card {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
            }}
            .stat-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
            .stat-value {{ font-size: 24px; font-weight: 700; color: #0f172a; }}
            .stat-value.highlight {{ color: #2563eb; }}

            .section-title {{
                font-size: 16px;
                font-weight: 600;
                color: #334155;
                margin-bottom: 12px;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 6px;
            }}
            .focus-grid {{
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin-bottom: 28px;
            }}
            .focus-card {{
                display: flex;
                align-items: center;
                gap: 12px;
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-left: 4px solid #ef4444;
                padding: 10px 14px;
                border-radius: 6px;
            }}
            .focus-badge {{
                background-color: #ef4444;
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .focus-title {{ font-size: 14px; font-weight: 600; color: #991b1b; }}
            .focus-count {{ font-size: 12px; color: #b91c1c; }}
            .no-focus {{ font-size: 14px; color: #166534; background-color: #f0fdf4; padding: 12px; border-radius: 6px; }}

            .chart-container {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                margin-bottom: 30px;
            }}
            .chart-row {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .topic-label {{
                width: 220px;
                display: flex;
                gap: 8px;
                font-size: 13px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .topic-code {{ font-weight: 700; color: #334155; min-width: 35px; }}
            .topic-name {{ color: #64748b; overflow: hidden; text-overflow: ellipsis; }}
            .bar-container {{
                flex-grow: 1;
                background-color: #f1f5f9;
                height: 16px;
                border-radius: 8px;
                overflow: hidden;
            }}
            .bar-fill {{
                height: 100%;
                border-radius: 8px;
            }}
            .bar-high {{ background-color: #ef4444; }}
            .bar-med {{ background-color: #3b82f6; }}
            .bar-zero {{ background-color: #cbd5e1; }}
            .count-badge {{
                width: 30px;
                text-align: right;
                font-size: 13px;
                font-weight: 600;
                color: #334155;
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
            <h1>Class Performance Summary</h1>
            <p>Mt. SAC Chemistry Workbook Analytics</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Class Average</div>
                <div class="stat-value highlight">{class_average}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Students Evaluated</div>
                <div class="stat-value">{total_students}</div>
            </div>
        </div>

        <div class="section-title">Primary Areas of Difficulty</div>
        <div class="focus-grid">
            {top_3_html}
        </div>

        <div class="section-title">Missed Topics Breakdown</div>
        <div class="chart-container">
            {chart_rows_html}
        </div>

        <div class="footer">
            Generated automatically by Mt. SAC Chemistry Workbook Tool
        </div>
    </body>
    </html>
    """