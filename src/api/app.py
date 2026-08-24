"""FastAPI app: chat endpoint + proposal confirm/cancel (Rule 5).

The agent prepares proposals; execution happens ONLY via POST /proposals/{id}/confirm,
enforced server-side. Access scope comes from the bearer-token session.
"""

from __future__ import annotations

import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.loop import iter_agent, run_agent
from src.agent.proposals import STORE
from src.config import ROOT
from src.data.repository import Repository, Session

from .auth import demo_tokens, session_from_token

app = FastAPI(title="ParcelPilot AI Support Agent")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


class TraceStepOut(BaseModel):
    tool: str
    args: dict
    result: dict


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceStepOut]
    iterations: int
    provider: str


@app.get("/health")
def health() -> dict:
    from src.config import get_settings

    s = get_settings()
    # Report which provider is active and whether keys are present (never the
    # keys themselves) so a deploy can be debugged from the browser.
    return {
        "status": "ok",
        "llm_provider": s.llm_provider,
        "llm_fallback_provider": s.llm_fallback_provider or None,
        "groq_key_set": bool(s.groq_api_key),
        "gemini_key_set": bool(s.gemini_api_key),
        "demo_tokens": demo_tokens(),
    }


@app.get("/me")
def me(session: Session = Depends(session_from_token)) -> dict:
    return {"role": session.role, "account_id": session.account_id}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, session: Session = Depends(session_from_token)) -> ChatResponse:
    result = run_agent(session, req.message, history=req.history)
    trace = []
    for s in result.trace:
        try:
            parsed = json.loads(s.result)
        except json.JSONDecodeError:
            parsed = {"raw": s.result}
        trace.append(TraceStepOut(tool=s.tool, args=s.args, result=parsed))
    return ChatResponse(answer=result.answer, trace=trace,
                        iterations=result.iterations, provider=result.provider)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, session: Session = Depends(session_from_token)):
    """Server-sent events: streams tool_call / tool_result / final as they happen."""
    def gen():
        try:
            for ev in iter_agent(session, req.message, history=req.history):
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as e:  # surface errors to the UI instead of hanging
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/ops/signals")
def ops_signals(session: Session = Depends(session_from_token)) -> dict:
    """Problem 1: proactive issue-detection dashboard. Internal ops only."""
    if not session.is_internal:
        raise HTTPException(403, "internal_ops only")
    from src.ops.signals import build_dashboard

    return build_dashboard()


@app.get("/proposals")
def list_proposals(session: Session = Depends(session_from_token)) -> dict:
    items = STORE.list_for(account_id=session.account_id, is_internal=session.is_internal)
    return {"proposals": [p.to_dict() for p in items]}


@app.post("/proposals/{proposal_id}/confirm")
def confirm_proposal(proposal_id: str,
                     session: Session = Depends(session_from_token)) -> dict:
    try:
        p = STORE.confirm(proposal_id, account_id=session.account_id,
                          is_internal=session.is_internal)
    except KeyError:
        raise HTTPException(404, "proposal not found") from None
    except PermissionError:
        raise HTTPException(403, "proposal belongs to another account") from None
    except ValueError as e:
        raise HTTPException(409, str(e)) from None
    return p.to_dict()


@app.post("/proposals/{proposal_id}/cancel")
def cancel_proposal(proposal_id: str,
                    session: Session = Depends(session_from_token)) -> dict:
    p = STORE.get(proposal_id)
    if p is None:
        raise HTTPException(404, "proposal not found")
    if not session.is_internal and p.account_id != session.account_id:
        raise HTTPException(403, "proposal belongs to another account")
    return STORE.cancel(proposal_id).to_dict()


# Warm the retrieval index at startup so the first chat is fast.
@app.on_event("startup")
def _warm() -> None:
    from src.retrieval.index import get_index

    Repository()  # opens DB (fails fast if not ingested)
    get_index()


# Serve the built React app (single-container hosting). API routes above take
# precedence; this static mount is the fallback for "/" and assets.
_DIST = ROOT / "frontend" / "dist"
if _DIST.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
