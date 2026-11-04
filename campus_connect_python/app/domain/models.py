from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    GREEN = "VERDE"
    YELLOW = "AMARILLO"
    RED = "ROJO"


class StudentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ObserverCategory(str, Enum):
    CONVIVENCIA = "Convivencial"
    ACADEMICA = "Académica"
    FAMILIAR = "Familiar/Entorno"
    GRAVE = "Grave"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(slots=True)
class Attendance:
    student_id: str
    date: date
    present: bool
    justification: Optional[str] = None
    noted_by: Optional[str] = None


@dataclass(slots=True)
class Grade:
    student_id: str
    subject: str
    period: str
    value: float


@dataclass(slots=True)
class ObserverRecord:
    student_id: str
    category: ObserverCategory
    description: str
    severity: AlertSeverity = AlertSeverity.MEDIUM
    created_at: Optional[datetime] = None


@dataclass(slots=True)
class Student:
    id: str
    full_name: str
    document_number: str
    grade: str
    status: StudentStatus = StudentStatus.ACTIVE
    attendance_records: list[Attendance] = field(default_factory=list)
    grades: list[Grade] = field(default_factory=list)
    observer_records: list[ObserverRecord] = field(default_factory=list)
    absent_parent_meetings: int = 0
    warnings_this_month: int = 0


@dataclass(slots=True)
class RiskReport:
    final_score: int
    risk_level: RiskLevel
    triggers: list[str]
    recommended_actions: list[str]
    should_notify_immediately: bool = False

    def __post_init__(self) -> None:
        self.final_score = max(0, min(100, self.final_score))
        self.triggers = list(dict.fromkeys(self.triggers))
        self.recommended_actions = list(dict.fromkeys(self.recommended_actions))
