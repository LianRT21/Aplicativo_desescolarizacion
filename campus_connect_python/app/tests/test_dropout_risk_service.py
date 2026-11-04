from datetime import date

from app.domain.models import (
    AlertSeverity,
    Attendance,
    Grade,
    ObserverCategory,
    ObserverRecord,
    RiskLevel,
    RiskReport,
    Student,
    StudentStatus,
)
from app.services.dropout_risk_service import DropoutRiskEvaluationService


def test_risk_report_marks_red_when_multiple_alerts_exist():
    student = Student(
        id="stu-001",
        full_name="Ana Gómez",
        document_number="1012345678",
        grade="11A",
        status=StudentStatus.ACTIVE,
        attendance_records=[
            Attendance(student_id="stu-001", date=date(2026, 9, 1), present=False),
            Attendance(student_id="stu-001", date=date(2026, 9, 2), present=False),
            Attendance(student_id="stu-001", date=date(2026, 9, 3), present=False),
            Attendance(student_id="stu-001", date=date(2026, 9, 4), present=False),
            Attendance(student_id="stu-001", date=date(2026, 9, 5), present=True),
            Attendance(student_id="stu-001", date=date(2026, 9, 6), present=False),
        ],
        grades=[
            Grade(student_id="stu-001", subject="Matemáticas", period="Corte 1", value=2.8),
            Grade(student_id="stu-001", subject="Física", period="Corte 1", value=3.2),
            Grade(student_id="stu-001", subject="Química", period="Corte 1", value=2.7),
            Grade(student_id="stu-001", subject="Español", period="Corte 1", value=3.5),
            Grade(student_id="stu-001", subject="Matemáticas", period="Corte 2", value=2.1),
            Grade(student_id="stu-001", subject="Física", period="Corte 2", value=2.6),
            Grade(student_id="stu-001", subject="Química", period="Corte 2", value=2.3),
            Grade(student_id="stu-001", subject="Español", period="Corte 2", value=3.0),
        ],
        observer_records=[
            ObserverRecord(
                student_id="stu-001",
                category=ObserverCategory.FAMILIAR,
                description="Inasistencia del acudiente a la citación.",
                severity=AlertSeverity.MEDIUM,
            ),
            ObserverRecord(
                student_id="stu-001",
                category=ObserverCategory.FAMILIAR,
                description="Problemas familiares con apoyo insuficiente.",
                severity=AlertSeverity.HIGH,
            ),
            ObserverRecord(
                student_id="stu-001",
                category=ObserverCategory.CONVIVENCIA,
                description="Convivencia conflictiva con pares.",
                severity=AlertSeverity.MEDIUM,
            ),
        ],
        absent_parent_meetings=2,
        warnings_this_month=3,
    )

    report = DropoutRiskEvaluationService().evaluate(student)

    assert isinstance(report, RiskReport)
    assert report.risk_level == RiskLevel.RED
    assert report.final_score >= 60
    assert any("inasistencia" in trigger.lower() for trigger in report.triggers)
    assert report.recommended_actions
    assert report.should_notify_immediately is True


def test_risk_report_handles_green_case():
    student = Student(
        id="stu-002",
        full_name="Luis Pérez",
        document_number="1098765432",
        grade="8B",
        status=StudentStatus.ACTIVE,
        attendance_records=[
            Attendance(student_id="stu-002", date=date(2026, 9, 1), present=True),
            Attendance(student_id="stu-002", date=date(2026, 9, 2), present=True),
            Attendance(student_id="stu-002", date=date(2026, 9, 3), present=True),
            Attendance(student_id="stu-002", date=date(2026, 9, 4), present=True),
            Attendance(student_id="stu-002", date=date(2026, 9, 5), present=True),
        ],
        grades=[
            Grade(student_id="stu-002", subject="Matemáticas", period="Corte 1", value=4.2),
            Grade(student_id="stu-002", subject="Español", period="Corte 1", value=4.5),
            Grade(student_id="stu-002", subject="Sociales", period="Corte 1", value=4.0),
            Grade(student_id="stu-002", subject="Matemáticas", period="Corte 2", value=4.4),
            Grade(student_id="stu-002", subject="Español", period="Corte 2", value=4.6),
            Grade(student_id="stu-002", subject="Sociales", period="Corte 2", value=4.1),
        ],
        observer_records=[],
        absent_parent_meetings=0,
        warnings_this_month=0,
    )

    report = DropoutRiskEvaluationService().evaluate(student)

    assert report.risk_level == RiskLevel.GREEN
    assert report.final_score < 60
    assert report.should_notify_immediately is False
