import base64
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .detector import detect
from .llm import ask

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class DetectRequest(BaseModel):
    image: str  # base64-encoded JPEG


class AskRequest(BaseModel):
    objects: list[dict]
    question: str
    image: Optional[str] = None  # base64-encoded JPEG of current frame


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/detect")
def detect_endpoint(req: DetectRequest):
    try:
        image_bytes = base64.b64decode(req.image)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")
    objects = detect(image_bytes)
    return {"objects": objects}


@app.post("/ask")
def ask_endpoint(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    answer = ask(req.objects, req.question, req.image)
    return {"answer": answer}
