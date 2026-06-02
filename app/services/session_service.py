from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions.custom_exceptions import ConflictError, NotFoundError, ValidationError
from app.models.session import InterviewSession, SessionStatus
from app.schemas.session_schema import SessionStart, SessionUpdate
from app.utils.logger import logger


class SessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start_session(self, payload: SessionStart) -> InterviewSession:
        self._ensure_no_active_session(payload.candidate_id)
        now = datetime.now(timezone.utc)
        session = InterviewSession(
            candidate_id=payload.candidate_id,
            status=SessionStatus.ACTIVE,
            started_at=now,
            updated_at=now,
            created_at=now,
        )
        self.db.add(session)
        self._commit_or_rollback("starting session", candidate_id=payload.candidate_id)
        self.db.refresh(session)
        logger.info(
            "Session Started: session_id=%s candidate_id=%s status=%s",
            session.id,
            session.candidate_id,
            session.status,
        )
        return session

    def list_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        status: SessionStatus | None = None,
    ) -> list[InterviewSession]:
        query = (
            select(InterviewSession)
            .order_by(InterviewSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            query = query.where(InterviewSession.status == status)
        try:
            sessions = list(self.db.scalars(query).all())
        except SQLAlchemyError:
            logger.exception(
                "Database Error while listing sessions: skip=%s limit=%s status=%s",
                skip,
                limit,
                status,
            )
            raise

        logger.info(
            "Sessions Listed: count=%s skip=%s limit=%s status=%s",
            len(sessions),
            skip,
            limit,
            status,
        )
        return sessions

    def get_session(self, session_id: UUID) -> InterviewSession:
        try:
            session = self.db.get(InterviewSession, session_id)
        except SQLAlchemyError:
            logger.exception("Database Error while getting session: session_id=%s", session_id)
            raise

        if session is None:
            logger.warning("Validation Error: session_id=%s was not found", session_id)
            raise NotFoundError(f"Interview session with id {session_id} was not found")
        return session

    def update_session(self, session_id: UUID, payload: SessionUpdate) -> InterviewSession:
        session = self.get_session(session_id)
        update_data = payload.model_dump(exclude_unset=True)

        if session.status == SessionStatus.ENDED:
            logger.warning("Validation Error: ended session cannot be updated session_id=%s", session_id)
            raise ValidationError("Ended sessions cannot be updated")

        self._validate_update_payload(update_data)

        candidate_id = update_data.get("candidate_id", session.candidate_id)
        started_at = update_data.get("started_at", session.started_at)
        ended_at = update_data.get("ended_at", session.ended_at)
        status = update_data.get("status", session.status)

        if status == SessionStatus.ACTIVE:
            self._ensure_no_active_session(candidate_id, exclude_session_id=session.id)

        if ended_at is not None:
            if ended_at <= started_at:
                logger.warning(
                    "Validation Error: ended_at must be later than started_at session_id=%s",
                    session_id,
                )
                raise ValidationError("ended_at must be later than started_at")
            if status != SessionStatus.ENDED:
                logger.warning(
                    "Validation Error: ended_at requires ENDED status session_id=%s status=%s",
                    session_id,
                    status,
                )
                raise ValidationError("status must be ENDED when ended_at is provided")

        for field, value in update_data.items():
            setattr(session, field, value)

        session.updated_at = datetime.now(timezone.utc)
        self._commit_or_rollback("updating session", session_id=session.id)
        self.db.refresh(session)
        logger.info(
            "Session Updated: session_id=%s candidate_id=%s status=%s",
            session.id,
            session.candidate_id,
            session.status,
        )
        return session

    def pause_session(self, session_id: UUID) -> InterviewSession:
        session = self.get_session(session_id)
        if session.status != SessionStatus.ACTIVE:
            logger.warning(
                "Validation Error: only ACTIVE sessions can be paused session_id=%s status=%s",
                session.id,
                session.status,
            )
            raise ValidationError("Only ACTIVE sessions can be paused")
        session.status = SessionStatus.PAUSED
        session.updated_at = datetime.now(timezone.utc)
        self._commit_or_rollback("pausing session", session_id=session.id)
        self.db.refresh(session)
        logger.info(
            "Session Paused: session_id=%s candidate_id=%s",
            session.id,
            session.candidate_id,
        )
        return session

    def resume_session(self, session_id: UUID) -> InterviewSession:
        session = self.get_session(session_id)
        if session.status != SessionStatus.PAUSED:
            logger.warning(
                "Validation Error: only PAUSED sessions can be resumed session_id=%s status=%s",
                session.id,
                session.status,
            )
            raise ValidationError("Only PAUSED sessions can be resumed")

        self._ensure_no_active_session(session.candidate_id, exclude_session_id=session.id)
        session.status = SessionStatus.ACTIVE
        session.updated_at = datetime.now(timezone.utc)
        self._commit_or_rollback("resuming session", session_id=session.id)
        self.db.refresh(session)
        logger.info(
            "Session Resumed: session_id=%s candidate_id=%s",
            session.id,
            session.candidate_id,
        )
        return session

    def end_session(self, session_id: UUID) -> InterviewSession:
        session = self.get_session(session_id)
        if session.status == SessionStatus.ENDED:
            logger.warning("Validation Error: session already ended session_id=%s", session.id)
            raise ValidationError("Session has already ended")

        now = datetime.now(timezone.utc)
        session.status = SessionStatus.ENDED
        session.ended_at = now
        session.updated_at = now
        self._commit_or_rollback("ending session", session_id=session.id)
        self.db.refresh(session)
        logger.info(
            "Session Ended: session_id=%s candidate_id=%s ended_at=%s",
            session.id,
            session.candidate_id,
            session.ended_at,
        )
        return session

    def _ensure_no_active_session(
        self,
        candidate_id: str,
        exclude_session_id: UUID | None = None,
    ) -> None:
        query = select(InterviewSession).where(
            InterviewSession.candidate_id == candidate_id,
            InterviewSession.status == SessionStatus.ACTIVE,
        )
        if exclude_session_id is not None:
            query = query.where(InterviewSession.id != exclude_session_id)

        try:
            existing_session = self.db.scalar(query.limit(1))
        except SQLAlchemyError:
            logger.exception(
                "Database Error while checking active session: candidate_id=%s",
                candidate_id,
            )
            raise

        if existing_session is not None:
            logger.warning(
                "Validation Error: duplicate ACTIVE session candidate_id=%s existing_session_id=%s",
                candidate_id,
                existing_session.id,
            )
            raise ConflictError(
                f"Candidate {candidate_id} already has an ACTIVE interview session"
            )

    @staticmethod
    def _validate_update_payload(update_data: dict[str, object]) -> None:
        required_fields = ("candidate_id", "status", "started_at")
        null_fields = [
            field for field in required_fields if field in update_data and update_data[field] is None
        ]
        if null_fields:
            fields = ", ".join(null_fields)
            logger.warning("Validation Error: update payload contains null fields=%s", fields)
            raise ValidationError(f"Fields cannot be null: {fields}")

    def _commit_or_rollback(self, action: str, **context: object) -> None:
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            context_text = " ".join(f"{key}={value}" for key, value in context.items())
            logger.exception("Database Error while %s: %s", action, context_text)
            raise
