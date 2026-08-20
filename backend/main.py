from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Optional
from dotenv import load_dotenv
from processing import process_assessment, get_class_data
import io
import pandas as pd
from fastapi.responses import StreamingResponse
from filegen import file_generator_sync
import asyncio
from pathlib import Path
from fastapi import HTTPException

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
async def download_zip(test_file: UploadFile = File(...),
                        student_file: Optional[UploadFile] = File(None),
                        concatenate_files: bool = Form(False),
                        print_ready: bool = Form(False)):
    #process and return a downloadable ZIP
    test_contents = await test_file.read()
    student_contents = None

    ext = Path(test_file.filename).suffix.lower()

    #finds the file type and reads it into a pandas dataframe
    if ext in ['.xlsx', '.xls']:
        try:
            test_df = pd.read_excel(io.BytesIO(test_contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail="Error reading Assessment file")
        
    elif ext == '.csv':
        try:
            test_df = pd.read_csv(io.BytesIO(test_contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail="Error reading Assessment file")
        
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")  

    student_info_df = None
    if student_file is not None:
        student_contents = await student_file.read()
        
        try:
            student_info_df = pd.read_excel(io.BytesIO(student_contents), header=None)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Error reading student information file")

    results = process_assessment(test_df, student_info_df)
    class_data = get_class_data(results)

    # todo, pass it in    
    zip_buffer = await asyncio.to_thread(file_generator_sync, results, test_file.filename, class_data, concatenate_files, print_ready)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=student_reports.zip"}
    )