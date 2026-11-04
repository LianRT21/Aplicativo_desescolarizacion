from __future__ import annotations

from app.core.security import AuthContext, UserRole
from app.domain.models import RiskLevel, Student
from app.services.dropout_risk_service import DropoutRiskEvaluationService


class DashboardService:
    def __init__(self):
        self.risk_service = DropoutRiskEvaluationService()

    def get_dashboard_summary(self, students: list[Student], auth: AuthContext):
        if auth.role == UserRole.ACUDIENTE:
            students = [student for student in students if student.id == auth.user_id]

        summary = {
            "total_students": len(students),
            "green": 0,
            "yellow": 0,
            "red": 0,
            "students_in_risk": [],
        }

        for student in students:
            report = self.risk_service.evaluate(student)
            if report.risk_level == RiskLevel.GREEN:
                summary["green"] += 1
            elif report.risk_level == RiskLevel.YELLOW:
                summary["yellow"] += 1
            else:
                summary["red"] += 1
            summary["students_in_risk"].append({
                "student_id": student.id,
                "student_name": student.full_name,
                "score": report.final_score,
                "risk_level": report.risk_level.value,
            })

        summary["students_in_risk"] = sorted(
            summary["students_in_risk"],
            key=lambda item: item["score"],
            reverse=True,
        )
        return summary
