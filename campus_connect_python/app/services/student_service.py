from __future__ import annotations

from app.core.security import AuthContext, UserRole, require_role
from app.domain.models import Student
from app.repositories.memory_repository import InMemoryRepository


class StudentService:
    def __init__(self, repository: InMemoryRepository | None = None):
        self.repository = repository or InMemoryRepository()

    @require_role(UserRole.DIRECTIVO, UserRole.DOCENTE)
    def create_student(self, student: Student, auth: AuthContext) -> Student:
        self.repository.add(student, student.id)
        return student

    @require_role(UserRole.DIRECTIVO, UserRole.DOCENTE, UserRole.ACUDIENTE)
    def get_student(self, student_id: str, auth: AuthContext) -> Student:
        student = self.repository.get_by_id(student_id)
        if student is None:
            raise ValueError(f"Student {student_id} not found")
        if auth.role == UserRole.ACUDIENTE and student.id != auth.user_id:
            raise PermissionError("Acudiente can only access their own student")
        return student
