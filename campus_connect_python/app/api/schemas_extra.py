from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class StudentCreateRequest(BaseModel):
    student_id: str
    full_name: str
    document_number: str
    grade: str | None = None
    status: str = "ACTIVE"


class AttendanceCreateRequest(BaseModel):
    student_id: str
    attendance_date: str
    present: bool
    justification: str | None = None


class GradeCreateRequest(BaseModel):
    student_id: str
    subject: str
    period: str
    value: float = Field(..., ge=0.0, le=5.0)


class ObservationCreateRequest(BaseModel):
    student_id: str
    category: str
    description: str
    severity: str = "MEDIUM"
