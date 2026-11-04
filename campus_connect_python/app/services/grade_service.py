from __future__ import annotations

from app.core.security import AuthContext, UserRole, require_role
from app.domain.models import Grade, Student
from app.repositories.memory_repository import InMemoryRepository


class GradeService:
    def __init__(self, repository: InMemoryRepository | None = None):
        self.repository = repository or InMemoryRepository()

    @require_role(UserRole.DOCENTE, UserRole.DIRECTIVO)
    def register_grade(self, grade: Grade, auth: AuthContext) -> Grade:
        key = f"{grade.student_id}:{grade.subject}:{grade.period}"
        self.repository.add(grade, key)
        return grade

    @require_role(UserRole.DOCENTE, UserRole.DIRECTIVO, UserRole.ACUDIENTE)
    def list_grades(self, student_id: str, auth: AuthContext) -> list[Grade]:
        return [
            item for item in self.repository.list_all() if getattr(item, "student_id", None) == student_id
        ]
