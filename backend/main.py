from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from processing import process_assessment
import io
import pandas as pd
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

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read() # read file content

    df = pd.read_excel(io.BytesIO(contents)) # feed it into pandas in bytes
    
    analysis_result = process_assessment(df)
    # run and return
    return analysis_result
