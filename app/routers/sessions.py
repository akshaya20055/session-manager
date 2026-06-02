from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from app.dependencies import DbSession
from app.models.session import SessionStatus
from app.schemas.session_schema import ErrorResponse, SessionRead, SessionStart, SessionUpdate
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Business validation failed.",
    },
    404: {
        "model": ErrorResponse,
        "description": "The requested interview session does not exist.",
    },
    409: {
        "model": ErrorResponse,
        "description": "The request conflicts with the current session state.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Request payload, query parameter, or path parameter validation failed.",
    },
    500: {
        "model": ErrorResponse,
        "description": "Unexpected server error.",
    },
}


@router.post(
    "/start",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start Interview Session",
    description=(
        "Starts a new interview session for a candidate. A candidate cannot have "
        "more than one ACTIVE session at the same time."
    ),
    response_description="The newly started interview session.",
    responses={
        201: {"description": "Interview session started successfully."},
        **ERROR_RESPONSES,
    },
)
def start_session(payload: SessionStart, db: DbSession) -> SessionRead:
    return SessionService(db).start_session(payload)


@router.get(
    "",
    response_model=list[SessionRead],
    summary="List Interview Sessions",
    description=(
        "Returns interview sessions ordered by most recent start time. Results can "
        "be paginated and optionally filtered by lifecycle status."
    ),
    response_description="A list of interview sessions.",
    responses={
        200: {"description": "Interview sessions returned successfully."},
        **ERROR_RESPONSES,
    },
)
def list_sessions(
    db: DbSession,
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination.",
        examples=[0],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of records to return.",
        examples=[25],
    ),
    status_filter: SessionStatus | None = Query(
        default=None,
        alias="status",
        description="Optional lifecycle status filter.",
        examples=[SessionStatus.ACTIVE],
    ),
) -> list[SessionRead]:
    return SessionService(db).list_sessions(skip=skip, limit=limit, status=status_filter)


@router.get(
    "/{session_id}",
    response_model=SessionRead,
    summary="Get Interview Session",
    description="Returns a single interview session by UUID.",
    response_description="The requested interview session.",
    responses={
        200: {"description": "Interview session returned successfully."},
        **ERROR_RESPONSES,
    },
)
def get_session(
    db: DbSession,
    session_id: UUID = Path(
        description="UUID of the interview session.",
        examples=["11111111-1111-1111-1111-111111111111"],
    ),
) -> SessionRead:
    return SessionService(db).get_session(session_id)


@router.put(
    "/{session_id}",
    response_model=SessionRead,
    summary="Update Interview Session",
    description=(
        "Updates editable fields on an interview session. Ended sessions cannot be "
        "updated. Use the dedicated lifecycle endpoints for pause, resume, and end "
        "operations whenever possible."
    ),
    response_description="The updated interview session.",
    responses={
        200: {"description": "Interview session updated successfully."},
        **ERROR_RESPONSES,
    },
)
def update_session(
    payload: SessionUpdate,
    db: DbSession,
    session_id: UUID = Path(
        description="UUID of the interview session to update.",
        examples=["11111111-1111-1111-1111-111111111111"],
    ),
) -> SessionRead:
    return SessionService(db).update_session(session_id, payload)


@router.post(
    "/{session_id}/pause",
    response_model=SessionRead,
    summary="Pause Interview Session",
    description="Pauses an ACTIVE interview session and updates its timestamp.",
    response_description="The paused interview session.",
    responses={
        200: {"description": "Interview session paused successfully."},
        **ERROR_RESPONSES,
    },
)
def pause_session(
    db: DbSession,
    session_id: UUID = Path(
        description="UUID of the ACTIVE interview session to pause.",
        examples=["11111111-1111-1111-1111-111111111111"],
    ),
) -> SessionRead:
    return SessionService(db).pause_session(session_id)


@router.post(
    "/{session_id}/resume",
    response_model=SessionRead,
    summary="Resume Interview Session",
    description=(
        "Resumes a PAUSED interview session. The candidate must not have another "
        "ACTIVE interview session."
    ),
    response_description="The resumed interview session.",
    responses={
        200: {"description": "Interview session resumed successfully."},
        **ERROR_RESPONSES,
    },
)
def resume_session(
    db: DbSession,
    session_id: UUID = Path(
        description="UUID of the PAUSED interview session to resume.",
        examples=["11111111-1111-1111-1111-111111111111"],
    ),
) -> SessionRead:
    return SessionService(db).resume_session(session_id)


@router.post(
    "/{session_id}/end",
    response_model=SessionRead,
    summary="End Interview Session",
    description=(
        "Ends an ACTIVE or PAUSED interview session. The endpoint sets status to "
        "ENDED, records ended_at, and updates updated_at."
    ),
    response_description="The ended interview session.",
    responses={
        200: {"description": "Interview session ended successfully."},
        **ERROR_RESPONSES,
    },
)
def end_session(
    db: DbSession,
    session_id: UUID = Path(
        description="UUID of the interview session to end.",
        examples=["11111111-1111-1111-1111-111111111111"],
    ),
) -> SessionRead:
    return SessionService(db).end_session(session_id)
