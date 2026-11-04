from __future__ import annotations

from datetime import date

from app.core.security import AuthContext, UserRole, require_role
from app.domain.models import Attendance, Student
from app.repositories.memory_repository import InMemoryRepository


class AttendanceService:
    def __init__(self, repository: InMemoryRepository | None = None):
        self.repository = repository or InMemoryRepository()

    @require_role(UserRole.DOCENTE, UserRole.DIRECTIVO)
    def register_attendance(self, attendance: Attendance, auth: AuthContext) -> Attendance:
        self.repository.add(attendance, f"{attendance.student_id}:{attendance.date.isoformat()}")
        return attendance

    @require_role(UserRole.DOCENTE, UserRole.DIRECTIVO, UserRole.ACUDIENTE)
    def get_attendance(self, student_id: str, auth: AuthContext) -> list[Attendance]:
        records = [
            item for item in self.repository.list_all() if getattr(item, "student_id", None) == student_id
        ]
        if auth.role == UserRole.ACUDIENTE:
            return records
        return records

    def mark_justification(self, student_id: str, attendance_date: date, justification: str, auth: AuthContext) -> Attendance:
        key = f"{student_id}:{attendance_date.isoformat()}"
        item = self.repository.get_by_id(key)
        if item is None:
            raise ValueError("Attendance record not found")
        item.justification = justification
        item.noted_by = auth.user_id
        return item
