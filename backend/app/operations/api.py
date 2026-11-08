from functools import lru_cache
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from .models import (
    Action,
    ChatRequest,
    ExecuteRequest,
    LoginRequest,
    ReviewRequest,
    POLICIES,
)
from .provider import plan, status, ProviderUnavailable
from .service import Operations

router = APIRouter(prefix="/ops", tags=["Working operations assistant"])


@lru_cache(maxsize=1)
def operations():
    return Operations()


def current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in to continue.")
    try:
        return operations().store.authenticate(authorization[7:])
    except PermissionError as e:
        raise HTTPException(401, str(e)) from None


def manager(user=Depends(current_user)):
    if user["role"] != "manager":
        raise HTTPException(403, "An authenticated manager is required.")
    return user


@router.post("/login")
def login(body: LoginRequest):
    try:
        return operations().store.login(body.username, body.password)
    except PermissionError as e:
        raise HTTPException(401, str(e)) from None


@router.post("/logout")
def logout(user=Depends(current_user), authorization: str = Header()):
    operations().store.logout(authorization[7:])
    return {"signed_out": True}


@router.get("/status")
def provider_status():
    return {
        "name": "AegisMesh AI",
        "environment": "controlled_lab",
        "data": "synthetic",
        "provider": status(),
        "runtime": "Actual SQLite ticket updates and downloadable CSV exports",
        "codex": "See docs/BUILD_WITH_CODEX.md for recorded engineering evidence.",
    }


@router.get("/workspace")
def workspace(user=Depends(current_user)):
    return {"user": user, "policies": POLICIES, **operations().dashboard(user)}


@router.get("/tickets/{ticket_id}/context")
def context(ticket_id: int, user=Depends(current_user)):
    with operations().store.transaction() as db:
        row = db.execute(
            "SELECT ticket_id,category,message FROM tickets WHERE ticket_id=?",
            (ticket_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Ticket not found.")
        return {**dict(row), "trust": "untrusted_customer_content"}


@router.post("/chat")
async def chat(body: ChatRequest, user=Depends(current_user)):
    if user["role"] == "auditor":
        raise HTTPException(403, "Auditors have read-only activity access.")
    ticket = context(body.ticket_context_id, user) if body.ticket_context_id else None
    try:
        result, provider = await plan(body.message, ticket)
    except ProviderUnavailable as e:
        raise HTTPException(503, str(e)) from None
    proposal = (
        operations().propose(user, result.action, result.explanation, provider)
        if result.action
        else None
    )
    return {
        "explanation": result.explanation,
        "proposal": proposal,
        "provider": provider,
        "context_used": ticket,
        "executed": False,
    }


@router.post("/proposals")
def propose(body: Action, user=Depends(current_user)):
    """Explicit tool-call test seam; uses the identical policy and executor path."""
    return operations().propose(
        user,
        body,
        "Explicit tool-call proposal; no model was invoked.",
        {
            "provider": "explicit_tool_call",
            "live_llm": False,
            "latency_ms": 0,
            "usage": None,
        },
    )


@router.post("/execute")
def execute(body: ExecuteRequest, user=Depends(current_user)):
    return operations().execute(user, body.proposal_id, body.action, body.approval_id)


@router.post("/approvals/{approval_id}/review")
def review(approval_id: str, body: ReviewRequest, user=Depends(manager)):
    return operations().review(user, approval_id, body.decision, body.comment)


@router.get("/exports/{export_id}")
def download(export_id: str, user=Depends(current_user)):
    report = operations().export(user, export_id)
    return Response(
        report["content"],
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{export_id}.csv"',
            "X-Content-SHA256": report["sha256"],
            "Cache-Control": "no-store",
        },
    )


def install(app):
    app.include_router(router, prefix="/api")

    @app.middleware("http")
    async def security_boundary(request, call_next):
        # Legacy routes are an authenticated simulation lab. They cannot be used
        # to bypass the new workspace's identities, approvals or business tools.
        path = request.url.path
        if (
            path.startswith("/api/")
            and not path.startswith("/api/ops/")
            and path != "/api/health"
        ):
            auth = request.headers.get("authorization", "")
            try:
                user = operations().store.authenticate(
                    auth[7:] if auth.startswith("Bearer ") else ""
                )
            except PermissionError:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    {
                        "detail": "Legacy lab APIs require an authenticated workspace manager."
                    },
                    status_code=401,
                )
            if user["role"] != "manager":
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    {"detail": "Legacy lab APIs are restricted to managers."},
                    status_code=403,
                )
        try:
            response = await call_next(request)
        except (PermissionError, LookupError, ValueError) as e:
            from fastapi.responses import JSONResponse

            code = (
                403
                if isinstance(e, PermissionError)
                else 404
                if isinstance(e, LookupError)
                else 409
            )
            response = JSONResponse({"detail": str(e)}, status_code=code)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
