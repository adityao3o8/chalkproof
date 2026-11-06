"""Pydantic request/response and LLM output schemas."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---- Input validation ----

class ProjectCreate(BaseModel):
    title: str
    objective: str

    @field_validator("title", "objective")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v.strip()


class ProjectOut(BaseModel):
    id: int
    title: str
    objective: str
    status: str
    research_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StepStatusOut(BaseModel):
    step: str
    status: str
    error: Optional[str] = None
    updated_at: datetime


class SourceOut(BaseModel):
    id: int
    type: str
    url: str
    title: str
    reliability_tier: str
    relevant_segment: Optional[str] = None
    video_verified: bool = True
    claim_count: int = 0


class ClaimOut(BaseModel):
    id: int
    block_id: str
    claim_text: str
    source_id: Optional[int]
    supporting_quote: str


# ---- Lesson structure (LLM output) ----

class LessonBlock(BaseModel):
    id: str
    type: str  # hook|concept|worked_example|practical|activity|knowledge_check|summary|videos|references
    title: str
    content: str
    estimated_minutes: float = Field(ge=0)


class LessonClaim(BaseModel):
    claim_text: str
    source_id: int  # temporary index into sources list during generation; remapped to DB ids
    supporting_quote: str
    block_id: str


class KnowledgeCheckItem(BaseModel):
    question: str
    answer: str
    explanation: str


class LessonContent(BaseModel):
    title: str
    objective: str
    blocks: list[LessonBlock]
    claims: list[LessonClaim] = Field(default_factory=list)
    knowledge_checks: list[KnowledgeCheckItem] = Field(default_factory=list)
    total_estimated_minutes: float = 45.0
    executable_examples: Optional[dict[str, Any]] = None

    def recomputed_minutes(self) -> float:
        return sum(b.estimated_minutes for b in self.blocks)


# ---- QC issue format ----

class QCIssue(BaseModel):
    id: str
    severity: Literal["high", "med", "low"]
    location_block_id: Optional[str] = None
    description: str
    evidence: str = ""
    suggested_fix: str = ""
    status: Literal["open", "accepted", "rejected", "edited"] = "open"
    category: str = "general"


class QCReportOut(BaseModel):
    id: int
    layer: int
    lesson_version_id: int
    summary: str
    score: Optional[float] = None
    issues: list[QCIssue]
    created_at: datetime


class QCIssueUpdate(BaseModel):
    action: Literal["accept", "reject", "edit"]
    edited_fix: Optional[str] = None


class BlockUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    estimated_minutes: Optional[float] = None


class LessonSave(BaseModel):
    content: LessonContent
    note: Optional[str] = "manual save"


class VersionOut(BaseModel):
    id: int
    version: int
    author: str
    note: Optional[str]
    created_at: datetime
    total_estimated_minutes: Optional[float] = None
