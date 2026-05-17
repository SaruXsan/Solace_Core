from __future__ import annotations

from pydantic import BaseModel


class RfiSectionOut(BaseModel):
    section: str
    title: str
    questions: list["RfiQuestionOut"]


class RfiQuestionOut(BaseModel):
    id: str
    question_code: str
    question_text: str
    sort_order: int
    answer_text: str | None = None
    answer_status: str | None = None


class RfiAnswerIn(BaseModel):
    answer_text: str
    status: str = "draft"


class EvidenceOut(BaseModel):
    id: str
    title: str
    control_id: str | None
    source_event_type: str | None
    digital_signature_hash: str
    created_at: str
