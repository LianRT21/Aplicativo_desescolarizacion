from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.courses import WEEKDAYS
from app.core.database import get_db
from app.core.security import UserRole
from app.db.models import CourseItem, ScheduleEntry, StudentAccountLink, StudentRecord, User

router = APIRouter(prefix="/api/v1/student", tags=["student portal"])


@router.get("/portal")
def get_student_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ESTUDIANTE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access only")

    link = db.query(StudentAccountLink).filter(StudentAccountLink.user_id == current_user.id).first()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    student = db.query(StudentRecord).filter(StudentRecord.student_id == link.student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    grade = student.grade or ""
    schedule_entries = (
        db.query(ScheduleEntry, User)
        .join(User, User.id == ScheduleEntry.teacher_id)
        .filter(ScheduleEntry.grade == grade)
        .order_by(ScheduleEntry.weekday, ScheduleEntry.period)
        .all()
    )
    course_items = (
        db.query(CourseItem)
        .filter(CourseItem.grade == grade)
        .order_by(CourseItem.event_date, CourseItem.subject)
        .all()
    )
    tasks = [
        {
            "subject": item.subject,
            "title": item.title,
            "description": item.description,
            "due_date": item.event_date,
        }
        for item in course_items
        if item.item_type == "TASK"
    ]
    events = [
        {
            "subject": item.subject,
            "title": item.title,
            "description": item.description,
            "date": item.event_date,
        }
        for item in course_items
        if item.item_type == "EVENT"
    ]
    today = date.today()
    months = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )
    today_label = f"{today.day} de {months[today.month - 1]} de {today.year}"
    selected_day = WEEKDAYS[today.weekday()] if today.weekday() < len(WEEKDAYS) else WEEKDAYS[0]

    return {
        "student": {
            "id": student.student_id,
            "full_name": student.full_name,
            "document_number": student.document_number,
            "grade": student.grade,
        },
        "dashboard": {"date": today_label},
        "schedule": {
            "days": list(WEEKDAYS),
            "selected_day": selected_day,
            "classes": [
                {
                    "subject": entry.subject,
                    "start": entry.starts_at,
                    "end": entry.ends_at,
                    "kind": "class",
                    "weekday": WEEKDAYS[entry.weekday],
                    "teacher_name": teacher.full_name,
                }
                for entry, teacher in schedule_entries
            ],
        },
        "tasks": tasks,
        "events": {
            "notice": f"{len(events)} eventos programados" if events else "No hay eventos programados.",
            "items": events,
        },
    }