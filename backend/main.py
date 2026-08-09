from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from processing import process_assessment, get_class_data
import io
import pandas as pd
from fastapi.responses import StreamingResponse
from filegen import file_generator_sync
import asyncio
load_dotenv()

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://mtsac-chem-workbook-tool.vercel.app/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ENVIRONMENT = os.getenv("ENVIRONMENT")
# world hello
@app.get("/")
async def read_root():
    return {
            "status": "ok, backend connected to front",
            "environment": ENVIRONMENT
            }

@app.post("/download-zip")
async def download_zip(test_file: UploadFile = File(...), student_file: UploadFile = File(...)):
    #process and return a downloadable ZIP
    test_contents = await test_file.read()
    student_contents = await student_file.read()
    
    test_df = pd.read_excel(io.BytesIO(test_contents))
    student_info_df = pd.read_excel(io.BytesIO(student_contents), header = None)

    results = process_assessment(test_df, student_info_df)
    class_data = get_class_data(results)

    # todo, pass it in    
    zip_buffer = await asyncio.to_thread(file_generator_sync, results, test_file.filename, class_data)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=student_reports.zip"}
    )