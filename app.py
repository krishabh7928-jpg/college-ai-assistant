import json
import logging
import os
import re
from datetime import date
from io import BytesIO
from pathlib import Path

import pymupdf
from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field

from tools.attendance import mark_attendance
from tools.calculator import calculate_attendance
from tools.timetable import find_day_timetable


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
FRONTEND_PATH = Path(__file__).resolve().parent / "web" / "index.html"
DEFAULT_TIMETABLE_PATH = Path(__file__).resolve().parent / "test_timetable.txt"

app = FastAPI(title="College AI Assistant")


class AttendanceCalculation(BaseModel):
    attended: float = Field(ge=0)
    total: float = Field(gt=0)


class AttendanceSubmission(BaseModel):
    student_name: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=120)
    attendance_date: date
    status: str


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    student_name: str = Field(default="Rishabh Kumar", max_length=120)
    document_text: str = Field(default="", max_length=200_000)


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    try:
        page = FRONTEND_PATH.read_text(encoding="utf-8")
    except OSError as error:
        logger.exception("Could not load the web interface")
        raise HTTPException(
            status_code=500,
            detail="The web interface could not be loaded.",
        ) from error
    return HTMLResponse(page)


@app.get("/api/health")
def health() -> dict[str, bool | str]:
    return {
        "status": "ok",
        "ai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
    }


@app.get("/api/default-document")
def default_document() -> dict[str, str]:
    if not DEFAULT_TIMETABLE_PATH.is_file():
        return {"name": "", "text": ""}
    try:
        text = DEFAULT_TIMETABLE_PATH.read_text(encoding="utf-8")
    except OSError as error:
        logger.exception("Could not load the default timetable")
        raise HTTPException(
            status_code=500,
            detail="The default timetable could not be loaded.",
        ) from error
    return {"name": DEFAULT_TIMETABLE_PATH.name, "text": text}


@app.post("/api/attendance/calculate")
def attendance_calculate(payload: AttendanceCalculation) -> dict[str, float]:
    try:
        percentage = calculate_attendance(payload.attended, payload.total)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"percentage": percentage}


@app.post("/api/attendance/mark")
def attendance_mark(payload: AttendanceSubmission) -> dict[str, dict[str, str]]:
    try:
        record = mark_attendance(
            payload.student_name,
            payload.subject,
            payload.attendance_date.isoformat(),
            payload.status,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"record": record}


def extract_document_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                pages = []
                for page in pdf:
                    page_text = page.get_text("text").strip()
                    if page_text:
                        pages.append(page_text)
                return "\n\n".join(pages)
        if suffix == ".docx":
            document = Document(BytesIO(content))
            return "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            )
        if suffix == ".txt":
            return content.decode("utf-8-sig")
    except (ValueError, UnicodeDecodeError, OSError) as error:
        raise HTTPException(
            status_code=422,
            detail="Could not read this file. Check that it is a valid PDF, DOCX, or UTF-8 text file.",
        ) from error
    except Exception as error:
        if suffix in {".pdf", ".docx"}:
            raise HTTPException(
                status_code=422,
                detail="Could not read this file. Check that it is a valid PDF, DOCX, or UTF-8 text file.",
            ) from error
        raise
    raise HTTPException(
        status_code=415,
        detail="Unsupported file type. Upload a PDF, DOCX, or TXT file.",
    )


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, str]:
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, DOCX, or TXT file.",
        )
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File is too large. The maximum upload size is 4 MB.",
        )
    text = extract_document_text(filename, content)
    return {"name": filename, "text": text}


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI answers are not configured. Add OPENAI_API_KEY under "
                "Vercel Project Settings > Environment Variables, then redeploy."
            ),
        )
    return OpenAI(api_key=api_key)


@app.post("/api/ask")
def ask_assistant(payload: AssistantQuestion) -> dict[str, object]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Enter a question.")

    day_names = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    for day_name in day_names:
        if re.search(rf"\b{day_name}\b", question, re.IGNORECASE):
            if not payload.document_text.strip():
                raise HTTPException(
                    status_code=422,
                    detail="Timetable data is not available. Upload a timetable first.",
                )
            entries = find_day_timetable(payload.document_text, day_name)
            return {
                "answer": (
                    "\n".join(f"• {entry}" for entry in entries)
                    if entries
                    else f"No timetable entries were found for {day_name}."
                ),
                "tool_used": "Timetable Tool",
            }

    client = _client()
    tools = [
        {
            "type": "function",
            "name": "calculate_attendance",
            "description": "Calculate attendance percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attended": {"type": "integer"},
                    "total": {"type": "integer"},
                },
                "required": ["attended", "total"],
            },
        },
        {
            "type": "function",
            "name": "mark_attendance",
            "description": "Mark student attendance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "status": {"type": "string", "enum": ["Present", "Absent"]},
                },
                "required": ["subject", "status"],
            },
        },
    ]
    instructions = f"""
You are College AI Assistant.
Student name: {payload.student_name or "Rishabh Kumar"}
Today's date: {date.today().isoformat()}
Use the Calculator Tool for attendance percentage.
Use the Attendance Tool when the student wants to mark attendance.
Use the supplied college document when relevant. Never invent information.
Always mention any tool used.
"""
    try:
        response = client.responses.create(
            model=MODEL_NAME,
            instructions=instructions,
            input=question,
            tools=tools,
        )
        tool_outputs = []
        tools_used = []
        for item in response.output:
            if item.type != "function_call":
                continue
            arguments = json.loads(item.arguments)
            if item.name == "calculate_attendance":
                result = {
                    "percentage": calculate_attendance(
                        arguments["attended"],
                        arguments["total"],
                    )
                }
                tools_used.append("Calculator Tool")
            elif item.name == "mark_attendance":
                result = mark_attendance(
                    payload.student_name or "Rishabh Kumar",
                    arguments["subject"],
                    date.today().isoformat(),
                    arguments["status"],
                )
                tools_used.append("Attendance Tool")
            else:
                continue
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                }
            )

        if tool_outputs:
            final_response = client.responses.create(
                model=MODEL_NAME,
                instructions="Give a clear answer based only on the tool results. Mention which tool was used.",
                input=[*response.output, *tool_outputs],
                tools=tools,
            )
            answer = final_response.output_text
        else:
            answer = response.output_text
    except OpenAIError as error:
        logger.exception("OpenAI request failed")
        raise HTTPException(
            status_code=502,
            detail="The AI service request failed. Check the API key and try again.",
        ) from error
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        logger.exception("Could not process the assistant response")
        raise HTTPException(
            status_code=502,
            detail="The assistant returned a response that could not be processed.",
        ) from error

    return {"answer": answer, "tool_used": ", ".join(tools_used)}
