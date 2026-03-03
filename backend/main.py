from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import agents, chroma_kb, db, llm

UPLOAD_DIR = Path("uploads")

app = FastAPI(title="Advisor-in-the-loop Retirement Drawdown Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if True else [],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


@app.on_event("startup")
# initialize app dependencies.
def startup_event() -> None:
    load_dotenv()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    db.seed_users()


class ProfileIn(BaseModel):
    profile_json: Dict[str, Any]


class RequestIn(BaseModel):
    question_text: str


class ChatIn(BaseModel):
    messages: List[Dict[str, Any]]


class ReportDraftIn(BaseModel):
    request_id: int


class ReportFinalIn(BaseModel):
    final_md: str


class AgentRefineIn(BaseModel):
    concerns: str
    instructions: Optional[str] = None


class LoginIn(BaseModel):
    passcode: str


def _require_api_key_or_401(request: Request) -> Optional[JSONResponse]:
    if request.method == "OPTIONS":
        return None
    if request.url.path == "/api/login":
        return None

    configured_api_key = os.getenv("AUTH_API_KEY", "").strip()
    if not configured_api_key:
        return JSONResponse(status_code=500, content={"detail": "AUTH_API_KEY is not configured"})

    provided_api_key = request.headers.get("x-api-key", "").strip()
    if not provided_api_key:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            provided_api_key = auth[7:].strip()

    if provided_api_key != configured_api_key:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return None


@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next):
    denied = _require_api_key_or_401(request)
    if denied is not None:
        return denied
    return await call_next(request)


@app.post("/api/login")
# simple passcode login.
def login(payload: LoginIn):
    configured_passcode = os.getenv("AUTH_PASSCODE", "").strip()
    if not configured_passcode:
        raise HTTPException(status_code=500, detail="AUTH_PASSCODE is not configured")
    if payload.passcode != configured_passcode:
        raise HTTPException(status_code=401, detail="Invalid passcode")
    return {"ok": True}


# Mock session
@app.get("/api/mock/session")
# mock session.
def mock_session(x_mock_user_id: Optional[int] = Header(default=1)):
    user = db.get_user(int(x_mock_user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user["id"], "role": user["role"], "name": user["name"]}


@app.post("/api/mock/switch")
# mock switch.
def mock_switch(payload: Dict[str, Any]):
    user = db.get_user(int(payload.get("user_id", 0)))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user["id"], "role": user["role"], "name": user["name"]}


# Profile endpoints
@app.get("/api/users/{user_id}/profile/latest")
# get profile latest.
def get_profile_latest(user_id: int):
    latest = db.get_profile_latest(user_id)
    if not latest:
        return None
    return latest


@app.post("/api/users/{user_id}/profile")
# post profile.
def post_profile(user_id: int, payload: ProfileIn, x_mock_user_id: Optional[int] = Header(default=1)):
    user = db.get_user(int(x_mock_user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return db.save_profile_version(user_id, payload.profile_json, user["role"])


# Requests
@app.post("/api/users/{user_id}/requests")
# create request.
def create_request(user_id: int, payload: RequestIn):
    latest = db.get_profile_latest(user_id)
    if not latest:
        raise HTTPException(status_code=400, detail="Profile required")
    profile_json = latest["profile_json"]

    intake = agents.build_intake_graph()
    state = intake.invoke({"question_text": payload.question_text, "profile_json": profile_json})
    structured = state.get("structured_questions", {})

    req = db.create_request(user_id, payload.question_text, structured)
    return {"request_id": req["id"], "structured_questions": structured, "missing": state.get("missing")}


@app.post("/api/users/{user_id}/chat")
# chat.
def chat(user_id: int, payload: ChatIn):
    latest = db.get_profile_latest(user_id)
    profile_json = latest["profile_json"] if latest else {}
    messages = payload.messages
    chat_graph = agents.build_chat_graph()
    state = chat_graph.invoke(
        {"user_id": user_id, "profile_json": profile_json, "messages": messages}
    )
    return {
        "assistant_message": state.get("assistant_message", ""),
        "actions": state.get("actions", []),
    }


@app.post("/api/users/{user_id}/chat/upload")
# chat upload.
async def chat_upload(user_id: int, file: UploadFile = File(...)):
    latest = db.get_profile_latest(user_id)
    if not latest:
        raise HTTPException(status_code=400, detail="Profile required")
    profile_json = latest["profile_json"]

    content = await file.read()
    storage_path = UPLOAD_DIR / f"{user_id}_{file.filename}"
    storage_path.write_bytes(content)

    patch = llm.extract_profile_patch_from_text(pdf_bytes=content)
    if not patch:
        raise HTTPException(status_code=400, detail="Could not extract profile fields from PDF")

    result = agents.apply_profile_patch_direct(user_id, profile_json, patch)
    return {
        "assistant_message": "Profile updated from PDF.",
        "actions": [{"tool": "apply_profile_patch", "result": result}],
    }


@app.get("/api/users/{user_id}/requests")
# list requests.
def list_requests(user_id: int):
    return db.list_requests(user_id)


@app.get("/api/reports/{report_id}")
# get report.
def get_report(report_id: int):
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report["citations"] = db.list_citations(report_id)
    return report


@app.get("/api/users/{user_id}/reports")
# list reports.
def list_reports(user_id: int, status: Optional[str] = None):
    if status is None:
        status = "APPROVED"
    return db.list_reports_for_user(user_id, status=status)


@app.put("/api/reports/{report_id}/final")
# put report final.
def put_report_final(report_id: int, payload: ReportFinalIn, x_mock_user_id: Optional[int] = Header(default=2)):
    user = db.get_user(int(x_mock_user_id))
    if not user or user["role"] != "ADVISOR":
        raise HTTPException(status_code=403, detail="Advisor only")
    db.update_report_final(report_id, payload.final_md)
    db.add_review_event(report_id, user["id"], "EDIT", "Advisor manual edit", {"type": "manual"})
    return {"ok": True}


@app.post("/api/reports/{report_id}/approve")
# approve report.
def approve_report(report_id: int, x_mock_user_id: Optional[int] = Header(default=2)):
    user = db.get_user(int(x_mock_user_id))
    if not user or user["role"] != "ADVISOR":
        raise HTTPException(status_code=403, detail="Advisor only")
    report = db.get_report(report_id)
    if report and not report.get("final_md"):
        db.update_report_final(report_id, report.get("draft_md", ""))
    db.set_report_status(report_id, "APPROVED")
    db.add_review_event(report_id, user["id"], "APPROVE", None, None)
    return {"ok": True}



@app.post("/api/reports/{report_id}/agent-refine")
# agent refine.
def agent_refine(report_id: int, payload: AgentRefineIn, x_mock_user_id: Optional[int] = Header(default=2)):
    user = db.get_user(int(x_mock_user_id))
    if not user or user["role"] != "ADVISOR":
        raise HTTPException(status_code=403, detail="Advisor only")

    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    req = db.get_request(report["request_id"])
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    latest = db.get_profile_latest(report["user_id"])
    if not latest:
        raise HTTPException(status_code=400, detail="Profile required")
    profile_json = latest["profile_json"]

    structured = json.loads(req["structured_questions_json"])
    refine = agents.build_refine_graph()
    state = refine.invoke(
        {
            "user_id": report["user_id"],
            "question_text": req["question_text"],
            "profile_json": profile_json,
            "structured_questions": structured,
            "concerns": payload.concerns,
            "previous_report_md": report.get("final_md") or report.get("draft_md") or "",
        }
    )

    db.update_report_draft(report_id, state["draft_md"])
    db.add_citations(report_id, state.get("citations", []))
    db.add_review_event(report_id, user["id"], "EDIT", payload.concerns, {"type": "agent_refine"})

    return {"draft_md": state["draft_md"], "citations": state.get("citations", [])}


@app.get("/api/advisor/requests")
# advisor requests.
def advisor_requests():
    return db.list_pending_requests()


@app.post("/api/advisor/retrieve")
# advisor retrieve.
def advisor_retrieve(payload: Dict[str, Any]):
    query = payload.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query required")
    return {"results": chroma_kb.retrieve_sources(query, n_results=5)}


@app.get("/api/requests/{request_id}/detail")
# request detail.
def request_detail(request_id: int):
    req = db.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    user = db.get_user(req["user_id"])
    latest = db.get_profile_latest(req["user_id"])
    profile_json = latest["profile_json"] if latest else None
    report = None
    for r in db.list_reports_for_user(req["user_id"]):
        if r["request_id"] == req["id"]:
            report = r
            break
    return {"request": req, "user": user, "profile": profile_json, "report": report}


@app.post("/api/requests/{request_id}/generate-report")
# generate report.
def generate_report(request_id: int, x_mock_user_id: Optional[int] = Header(default=2)):
    user = db.get_user(int(x_mock_user_id))
    if not user or user["role"] != "ADVISOR":
        raise HTTPException(status_code=403, detail="Advisor only")
    req = db.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    latest = db.get_profile_latest(req["user_id"])
    if not latest:
        raise HTTPException(status_code=400, detail="Profile required")
    profile_json = latest["profile_json"]
    structured = json.loads(req["structured_questions_json"])
    draft_graph = agents.build_draft_graph()
    state = draft_graph.invoke(
        {
            "user_id": req["user_id"],
            "question_text": req["question_text"],
            "profile_json": profile_json,
            "structured_questions": structured,
        }
    )
    report_id = db.create_report(request_id, req["user_id"], state["draft_md"])
    db.add_citations(report_id, state.get("citations", []))
    db.set_request_status(request_id, "UNDER_REVIEW")
    return {"report_id": report_id, "status": "UNDER_REVIEW"}
