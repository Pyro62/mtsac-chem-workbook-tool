from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from processing import process_assessment
import io
import pandas as pd
from fastapi.responses import StreamingResponse
from filegen import file_generator
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
async def download_zip(file: UploadFile = File(...)):
    #process and return a downloadable ZIP
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    results = process_assessment(df)
    
    zip_buffer = file_generator(results)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=student_reports.zip"}
    )