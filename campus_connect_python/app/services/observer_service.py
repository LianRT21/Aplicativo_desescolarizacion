from __future__ import annotations

from app.core.security import AuthContext, UserRole, require_role
from app.domain.models import ObserverRecord
from app.repositories.memory_repository import InMemoryRepository


class ObserverService:
    def __init__(self, repository: InMemoryRepository | None = None):
        self.repository = repository or InMemoryRepository()

    @require_role(UserRole.DOCENTE, UserRole.DIRECTIVO)
    def add_observation(self, record: ObserverRecord, auth: AuthContext) -> ObserverRecord:
        key = f"{record.student_id}:{len(self.repository.list_all()) + 1}"
        self.repository.add(record, key)
        return record

    @require_role(UserRole.DOCENTE, UserRole.DIRECTIVO, UserRole.ACUDIENTE)
    def list_observations(self, student_id: str, auth: AuthContext) -> list[ObserverRecord]:
        return [
            item for item in self.repository.list_all() if getattr(item, "student_id", None) == student_id
        ]
