from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, TypeVar, Generic

T = TypeVar("T")


@dataclass
class InMemoryRepository(Generic[T]):
    storage: Dict[str, T] = field(default_factory=dict)

    def add(self, item: T, item_id: str | None = None) -> str:
        key = item_id or getattr(item, "id", None) or str(len(self.storage) + 1)
        self.storage[key] = item
        return key

    def get_by_id(self, item_id: str) -> T | None:
        return self.storage.get(item_id)

    def list_all(self) -> List[T]:
        return list(self.storage.values())

    def update(self, item_id: str, item: T) -> T:
        self.storage[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        self.storage.pop(item_id, None)
