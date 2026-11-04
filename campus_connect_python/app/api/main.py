from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.api.auth import router as auth_router
from app.api.courses import router as courses_router
from app.api.school import router as school_router
from app.api.student_portal import router as student_portal_router
from app.api.schemas import RiskReportResponse, StudentRiskRequest
from app.core.database import Base, engine
from app.db.models import User  # noqa: F401
from app.domain.models import (
    AlertSeverity,
    Attendance,
    Grade,
    ObserverCategory,
    ObserverRecord,
    Student,
    StudentStatus,
)
from app.services.dropout_risk_service import DropoutRiskEvaluationService

app = FastAPI(
    title="Campus Connect Risk Engine",
    version="0.1.0",
    description="Motor determinista de riesgo de desescolarización para instituciones educativas.",
)

Base.metadata.create_all(bind=engine)
app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(school_router)
app.include_router(student_portal_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/risk/evaluate", response_model=RiskReportResponse)
def evaluate_student_risk(student: StudentRiskRequest) -> RiskReportResponse:
    try:
        status = StudentStatus(student.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Estado inválido: {student.status}") from exc

    attendance_records = [
        Attendance(
            student_id=item.student_id,
            date=item.date,
            present=item.present,
            justification=item.justification,
            noted_by=item.noted_by,
        )
        for item in student.attendance_records
    ]

    grades = [
        Grade(
            student_id=item.student_id,
            subject=item.subject,
            period=item.period,
            value=item.value,
        )
        for item in student.grades
    ]

    observer_records = []
    for item in student.observer_records:
        try:
            category = ObserverCategory(item.category)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Categoría de observador inválida: {item.category}",
            ) from exc

        try:
            severity = AlertSeverity(item.severity)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Severidad inválida: {item.severity}",
            ) from exc

        observer_records.append(
            ObserverRecord(
                student_id=item.student_id,
                category=category,
                description=item.description,
                severity=severity,
            )
        )

    domain_student = Student(
        id=student.id,
        full_name=student.full_name,
        document_number=student.document_number,
        grade=student.grade,
        status=status,
        attendance_records=attendance_records,
        grades=grades,
        observer_records=observer_records,
        absent_parent_meetings=student.absent_parent_meetings,
        warnings_this_month=student.warnings_this_month,
    )

    report = DropoutRiskEvaluationService().evaluate(domain_student)

    return RiskReportResponse(
        final_score=report.final_score,
        risk_level=report.risk_level.value,
        triggers=report.triggers,
        recommended_actions=report.recommended_actions,
        should_notify_immediately=report.should_notify_immediately,
    )
