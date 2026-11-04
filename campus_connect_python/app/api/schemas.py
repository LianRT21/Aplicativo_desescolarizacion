from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class AttendanceInput(BaseModel):
    student_id: str
    date: date
    present: bool
    justification: str | None = None
    noted_by: str | None = None


class GradeInput(BaseModel):
    student_id: str
    subject: str
    period: str
    value: float = Field(..., ge=0.0, le=5.0)


class ObserverRecordInput(BaseModel):
    student_id: str
    category: str
    description: str
    severity: str = "MEDIUM"


class StudentRiskRequest(BaseModel):
    id: str
    full_name: str
    document_number: str
    grade: str
    status: str = "ACTIVE"
    attendance_records: list[AttendanceInput] = []
    grades: list[GradeInput] = []
    observer_records: list[ObserverRecordInput] = []
    absent_parent_meetings: int = 0
    warnings_this_month: int = 0


class RiskReportResponse(BaseModel):
    final_score: int
    risk_level: str
    triggers: list[str]
    recommended_actions: list[str]
    should_notify_immediately: bool
