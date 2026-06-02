from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.session import SessionStatus


class SessionBase(BaseModel):
    candidate_id: str = Field(
        max_length=100,
        description="Unique candidate identifier supplied by the interview platform.",
        examples=["candidate-001"],
    )
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        description="Current lifecycle status of the interview session.",
        examples=[SessionStatus.ACTIVE],
    )
    started_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the interview session started.",
        examples=["2026-06-01T10:00:00Z"],
    )
    ended_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the interview session ended. Null while active or paused.",
        examples=["2026-06-01T10:45:00Z"],
    )

    @field_validator("candidate_id", mode="before")
    @classmethod
    def normalize_candidate_id(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("candidate_id must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("candidate_id cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_session_state(self) -> "SessionBase":
        if self.ended_at is not None:
            if self.started_at is not None and self.ended_at <= self.started_at:
                raise ValueError("ended_at must be later than started_at")
            if self.status != SessionStatus.ENDED:
                raise ValueError("status must be ENDED when ended_at is provided")
        return self


class SessionStart(BaseModel):
    candidate_id: str = Field(
        max_length=100,
        description="Unique candidate identifier for the session to start.",
        examples=["candidate-001"],
    )

    @field_validator("candidate_id", mode="before")
    @classmethod
    def normalize_candidate_id(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("candidate_id must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("candidate_id cannot be empty")
        return normalized

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "candidate_id": "candidate-001",
            }
        }
    )


class SessionUpdate(BaseModel):
    candidate_id: str | None = Field(
        default=None,
        max_length=100,
        description="Replacement candidate identifier. Omit when it should not change.",
        examples=["candidate-001-updated"],
    )
    status: SessionStatus | None = Field(
        default=None,
        description="Replacement session status. Prefer lifecycle endpoints for pause, resume, and end.",
        examples=[SessionStatus.PAUSED],
    )
    started_at: datetime | None = Field(
        default=None,
        description="Replacement UTC start timestamp. Must be earlier than ended_at when both are present.",
        examples=["2026-06-01T10:00:00Z"],
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Replacement UTC end timestamp. Requires status to be ENDED.",
        examples=["2026-06-01T10:45:00Z"],
    )

    @field_validator("candidate_id", mode="before")
    @classmethod
    def normalize_optional_candidate_id(cls, value: object) -> str | None:
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("candidate_id must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("candidate_id cannot be empty")
        return normalized

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "candidate_id": "candidate-001-updated",
                },
                {
                    "status": "PAUSED",
                },
                {
                    "status": "ENDED",
                    "ended_at": "2026-06-01T10:45:00Z",
                },
            ]
        }
    )


class SessionRead(SessionBase):
    id: UUID = Field(
        description="System-generated UUID for the interview session.",
        examples=["11111111-1111-1111-1111-111111111111"],
    )
    started_at: datetime = Field(
        description="UTC timestamp when the interview session started.",
        examples=["2026-06-01T10:00:00Z"],
    )
    created_at: datetime = Field(
        description="UTC timestamp when the record was created.",
        examples=["2026-06-01T10:00:00Z"],
    )
    updated_at: datetime = Field(
        description="UTC timestamp when the record was last changed.",
        examples=["2026-06-01T10:15:00Z"],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "11111111-1111-1111-1111-111111111111",
                "candidate_id": "candidate-001",
                "status": "ACTIVE",
                "started_at": "2026-06-01T10:00:00Z",
                "updated_at": "2026-06-01T10:00:00Z",
                "ended_at": None,
                "created_at": "2026-06-01T10:00:00Z",
            }
        },
    )


class ErrorResponse(BaseModel):
    success: bool = Field(
        default=False,
        description="Always false for error responses.",
        examples=[False],
    )
    message: str = Field(
        description="Human-readable error message.",
        examples=["Interview session with id 11111111-1111-1111-1111-111111111111 was not found"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "Interview session was not found",
            }
        }
    )


class HealthResponse(BaseModel):
    status: str = Field(description="Current API health status.", examples=["ok"])

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})
