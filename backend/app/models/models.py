"""SQLModel tables for Chalkproof."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    objective: str
    status: str = Field(default="created")  # created|researching|generating|qc|ready|failed
    research_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Source(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    type: str  # web|book|video
    url: str = ""
    title: str = ""
    fetched_text: str = Field(default="", sa_column=Column(Text))
    reliability_tier: str = "medium"  # high|medium|low
    relevant_segment: Optional[str] = None  # video timestamps e.g. "2:30-8:15"
    video_verified: bool = True  # False when transcript unavailable
    metadata_json: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LessonVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    version: int
    content_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    author: str = "ai"  # ai|instructor
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lesson_version_id: int = Field(index=True)
    block_id: str
    claim_text: str = Field(sa_column=Column(Text))
    source_id: Optional[int] = Field(default=None, index=True)
    supporting_quote: str = Field(default="", sa_column=Column(Text))


class QCReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    layer: int  # 1|2
    lesson_version_id: int
    issues_json: list[Any] = Field(default_factory=list, sa_column=Column(JSON))
    summary: str = Field(default="", sa_column=Column(Text))
    score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StepStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    step: str  # research|generate|executable|qc1|qc2
    status: str = "pending"  # pending|running|done|failed
    error: Optional[str] = Field(default=None, sa_column=Column(Text))
    updated_at: datetime = Field(default_factory=datetime.utcnow)
