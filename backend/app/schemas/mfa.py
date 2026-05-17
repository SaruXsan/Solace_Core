from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class MfaChallengeCreateIn(BaseModel):
    user_id: UUID


class MfaChallengeOut(BaseModel):
    challenge_id: str
    destination_masked: str
    expires_at: str


class MfaVerifyIn(BaseModel):
    user_id: UUID
    otp: str = Field(min_length=6, max_length=6)


class MfaResendIn(BaseModel):
    user_id: UUID
