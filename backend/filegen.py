import io
import gc
import zipfile
from playwright.sync_api import sync_playwright
from processing import TOPIC_MAP

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

def file_generator_sync(results, filename, class_data):
    zip_buffer = io.BytesIO()

    # 1. Calculate class statistics
    total_students = len(results)
    class_html = generate_class_report_html(class_data, total_students)

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
            page.set_content(class_html)
            summary_pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
            )
            zip_file.writestr("00_Class_Summary_Report.pdf", summary_pdf_bytes)
            del summary_pdf_bytes  # Immediately free variable memory

            # --- Render Each Student Sequentially ---
            for student_id, test_results in results.items():
                html = generate_html(student_id, test_results)
                
                page.set_content(html)
                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
                )

                # Format filename
                raw_name = test_results.get('name', 'Student')
                safe_name = raw_name.replace(' ', '_').replace('/', '_')
                safe_id = str(student_id).replace(' ', '_').replace('/', '_')
                fname = f"{safe_name}_{safe_id}_review.pdf"

                # Write directly to ZIP buffer and wipe bytes from Python RAM
                zip_file.writestr(fname, pdf_bytes)
                del pdf_bytes
                
                # Force Python to release unreferenced byte objects immediately
                gc.collect()

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
            
            /* Overview Stats Grid */
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

            /* Focus Section */
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

            /* Bar Chart Section */
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