from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

app = FastAPI()

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT")
# world hello
@app.get("/")
async def read_root():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        db_status = 'connected'
    except Exception as e:
        db_status = 'failed:' + str(e)

    return {
            "status": "ok, backend connected to front",
            "environment": ENVIRONMENT,
            "db": db_status
            }
