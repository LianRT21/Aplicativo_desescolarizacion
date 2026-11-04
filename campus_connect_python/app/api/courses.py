from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.security import UserRole
from app.db.models import (
    CourseItem,
    CourseTeacherAssignment,
    GuardianStudentLink,
    ScheduleEntry,
    StudentAccountLink,
    StudentRecord,
    TeacherStudentLink,
    User,
)

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])

GRADES = tuple(str(grade) for grade in range(6, 12))
COMMON_SUBJECTS = (
    "Matemáticas",
    "Castellano",
    "Inglés",
    "Educación Física",
    "Sociales",
    "Tecnología",
    "Física",
    "Química",
    "Ciencias Naturales",
)
UPPER_GRADE_SUBJECTS = ("Ética", "Filosofía")
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")
PERIODS_PER_DAY = 7
COMMON_WEEKLY_PERIODS = {
    "Matemáticas": 5,
    "Castellano": 5,
    "Inglés": 4,
    "Educación Física": 2,
    "Sociales": 4,
    "Tecnología": 2,
    "Física": 2,
    "Química": 2,
    "Ciencias Naturales": 4,
}
UPPER_GRADE_WEEKLY_PERIODS = {
    **COMMON_WEEKLY_PERIODS,
    "Sociales": 3,
    "Física": 3,
    "Química": 3,
    "Ciencias Naturales": 3,
    "Ética": 1,
    "Filosofía": 1,
}


def subjects_for_grade(grade: str) -> tuple[str, ...]:
    if grade not in GRADES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Grade must be between 6 and 11")
    if grade in {"10", "11"}:
        return COMMON_SUBJECTS + UPPER_GRADE_SUBJECTS
    return COMMON_SUBJECTS


def _can_access_grade(current_user: User, grade: str, db: Session) -> bool:
    if current_user.role == UserRole.DIRECTIVO.value:
        return True
    if current_user.role == UserRole.DOCENTE.value:
        return (
            db.query(CourseTeacherAssignment)
            .filter(
                CourseTeacherAssignment.teacher_id == current_user.id,
                CourseTeacherAssignment.grade == grade,
            )
            .first()
            is not None
        )

    if current_user.role == UserRole.ESTUDIANTE.value:
        links = db.query(StudentAccountLink).filter(StudentAccountLink.user_id == current_user.id).all()
    elif current_user.role == UserRole.ACUDIENTE.value:
        links = db.query(GuardianStudentLink).filter(GuardianStudentLink.user_id == current_user.id).all()
    else:
        return False
    student_ids = [link.student_id for link in links]
    return (
        db.query(StudentRecord)
        .filter(StudentRecord.student_id.in_(student_ids), StudentRecord.grade == grade)
        .first()
        is not None
    )


def _period_times(period: int) -> tuple[str, str]:
    start_minutes = 7 * 60 + period * 50
    if period >= 3:
        start_minutes += 20
    if period >= 6:
        start_minutes += 40
    end_minutes = start_minutes + 50
    return (
        f"{start_minutes // 60:02d}:{start_minutes % 60:02d}",
        f"{end_minutes // 60:02d}:{end_minutes % 60:02d}",
    )


@router.get("")
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director access only")

    result = []
    for grade in GRADES:
        assignments = (
            db.query(CourseTeacherAssignment, User)
            .join(User, User.id == CourseTeacherAssignment.teacher_id)
            .filter(CourseTeacherAssignment.grade == grade)
            .order_by(CourseTeacherAssignment.subject)
            .all()
        )
        students = db.query(StudentRecord).filter(StudentRecord.grade == grade).order_by(StudentRecord.full_name).all()
        result.append(
            {
                "grade": grade,
                "subjects": list(subjects_for_grade(grade)),
                "assignments": [
                    {
                        "subject": assignment.subject,
                        "teacher_id": teacher.id,
                        "teacher_name": teacher.full_name,
                        "teacher_email": teacher.email,
                    }
                    for assignment, teacher in assignments
                ],
                "students": [
                    {
                        "student_id": student.student_id,
                        "full_name": student.full_name,
                        "document_number": student.document_number,
                    }
                    for student in students
                ],
            }
        )
    return result


@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director access only")
    teachers = db.query(User).filter(User.role == UserRole.DOCENTE.value).order_by(User.full_name).all()
    return [{"id": user.id, "email": user.email, "full_name": user.full_name} for user in teachers]


@router.get("/mine")
def list_my_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DOCENTE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access only")
    assignments = (
        db.query(CourseTeacherAssignment)
        .filter(CourseTeacherAssignment.teacher_id == current_user.id)
        .order_by(CourseTeacherAssignment.grade, CourseTeacherAssignment.subject)
        .all()
    )
    return [{"grade": item.grade, "subject": item.subject} for item in assignments]


@router.post("/{grade}/assignments", status_code=status.HTTP_201_CREATED)
def assign_teacher(
    grade: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director access only")
    allowed_subjects = subjects_for_grade(grade)
    subject = payload.get("subject")
    if subject not in allowed_subjects:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Subject is not offered in this grade")

    teacher = db.query(User).filter(User.email == payload.get("teacher_email"), User.role == UserRole.DOCENTE.value).first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher account not found")

    existing = (
        db.query(CourseTeacherAssignment)
        .filter(CourseTeacherAssignment.grade == grade, CourseTeacherAssignment.subject == subject)
        .first()
    )
    if existing is not None:
        if existing.teacher_id == teacher.id:
            return {"status": "ok", "grade": grade, "subject": subject, "teacher_id": teacher.id}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This course subject already has a teacher")

    assignment = CourseTeacherAssignment(grade=grade, subject=subject, teacher_id=teacher.id)
    db.add(assignment)
    db.commit()
    return {"status": "ok", "grade": grade, "subject": subject, "teacher_id": teacher.id}


@router.put("/{grade}/assignments/{subject}")
def replace_teacher(
    grade: str,
    subject: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director access only")
    if subject not in subjects_for_grade(grade):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Subject is not offered in this grade")
    teacher = db.query(User).filter(User.email == payload.get("teacher_email"), User.role == UserRole.DOCENTE.value).first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher account not found")
    assignment = (
        db.query(CourseTeacherAssignment)
        .filter(CourseTeacherAssignment.grade == grade, CourseTeacherAssignment.subject == subject)
        .first()
    )
    if assignment is None:
        assignment = CourseTeacherAssignment(grade=grade, subject=subject, teacher_id=teacher.id)
        db.add(assignment)
    else:
        assignment.teacher_id = teacher.id
    db.commit()
    return {"status": "ok", "grade": grade, "subject": subject, "teacher_id": teacher.id}


@router.post("/schedule/generate")
def generate_schedules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director access only")

    assignments = (
        db.query(CourseTeacherAssignment)
        .order_by(CourseTeacherAssignment.grade, CourseTeacherAssignment.subject)
        .all()
    )
    db.query(ScheduleEntry).delete(synchronize_session=False)
    course_slots: set[tuple[str, int, int]] = set()
    teacher_slots: set[tuple[str, int, int]] = set()
    day_load: dict[tuple[str, int], int] = defaultdict(int)
    teacher_day_load: dict[tuple[str, int], int] = defaultdict(int)
    entries = []

    for assignment in assignments:
        frequencies = UPPER_GRADE_WEEKLY_PERIODS if assignment.grade in {"10", "11"} else COMMON_WEEKLY_PERIODS
        weekly_periods = frequencies[assignment.subject]
        for _ in range(weekly_periods):
            candidates = sorted(
                ((weekday, period) for weekday in range(5) for period in range(PERIODS_PER_DAY)),
                key=lambda slot: (
                    day_load[(assignment.grade, slot[0])],
                    teacher_day_load[(assignment.teacher_id, slot[0])],
                    slot[1],
                    slot[0],
                ),
            )
            selected = next(
                (
                    slot
                    for slot in candidates
                    if (assignment.grade, *slot) not in course_slots
                    and (assignment.teacher_id, *slot) not in teacher_slots
                ),
                None,
            )
            if selected is None:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to schedule all assigned classes without conflicts")

            weekday, period = selected
            starts_at, ends_at = _period_times(period)
            entries.append(
                ScheduleEntry(
                    grade=assignment.grade,
                    subject=assignment.subject,
                    teacher_id=assignment.teacher_id,
                    weekday=weekday,
                    period=period,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )
            )
            course_slots.add((assignment.grade, weekday, period))
            teacher_slots.add((assignment.teacher_id, weekday, period))
            day_load[(assignment.grade, weekday)] += 1
            teacher_day_load[(assignment.teacher_id, weekday)] += 1

    db.add_all(entries)
    db.commit()
    return {"status": "ok", "scheduled_classes": len(entries)}


@router.get("/{grade}/schedule")
def get_course_schedule(
    grade: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subjects_for_grade(grade)
    if not _can_access_grade(current_user, grade, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course access only")
    entries = (
        db.query(ScheduleEntry, User)
        .join(User, User.id == ScheduleEntry.teacher_id)
        .filter(ScheduleEntry.grade == grade)
        .order_by(ScheduleEntry.weekday, ScheduleEntry.period)
        .all()
    )
    return [
        {
            "grade": entry.grade,
            "subject": entry.subject,
            "teacher_id": teacher.id,
            "teacher_name": teacher.full_name,
            "weekday": entry.weekday,
            "day": WEEKDAYS[entry.weekday],
            "period": entry.period,
            "start": entry.starts_at,
            "end": entry.ends_at,
        }
        for entry, teacher in entries
    ]


@router.get("/{grade}/items")
def get_course_items(
    grade: str,
    item_type: str | None = Query(default=None, pattern="^(TASK|EVENT)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subjects_for_grade(grade)
    if not _can_access_grade(current_user, grade, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course access only")
    query = db.query(CourseItem).filter(CourseItem.grade == grade)
    if item_type:
        query = query.filter(CourseItem.item_type == item_type)
    items = query.order_by(CourseItem.event_date, CourseItem.subject).all()
    return [_serialize_item(item) for item in items]


@router.post("/{grade}/items", status_code=status.HTTP_201_CREATED)
def create_course_item(
    grade: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subjects = subjects_for_grade(grade)
    if current_user.role != UserRole.DOCENTE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access only")

    item_type = payload.get("item_type")
    subject = payload.get("subject")
    if item_type not in {"TASK", "EVENT"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Item type must be TASK or EVENT")
    if subject not in subjects:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Subject is not offered in this grade")
    assignment = (
        db.query(CourseTeacherAssignment)
        .filter(
            CourseTeacherAssignment.grade == grade,
            CourseTeacherAssignment.subject == subject,
            CourseTeacherAssignment.teacher_id == current_user.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this subject and course")

    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    event_date = (payload.get("date") or "").strip()
    if not title or not description or len(event_date) != 10:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title, description, and date are required")

    item = CourseItem(
        grade=grade,
        item_type=item_type,
        subject=subject,
        title=title,
        description=description,
        event_date=event_date,
        created_by=current_user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_item(item)


def _serialize_item(item: CourseItem) -> dict[str, str]:
    return {
        "id": item.id,
        "grade": item.grade,
        "item_type": item.item_type,
        "subject": item.subject,
        "title": item.title,
        "description": item.description,
        "date": item.event_date,
    }