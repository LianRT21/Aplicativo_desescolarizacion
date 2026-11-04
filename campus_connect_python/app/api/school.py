from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.security import UserRole, get_password_hash
from app.db.models import (
    AttendanceRecord,
    CourseTeacherAssignment,
    GradeRecord,
    GuardianStudentLink,
    ObserverRecordDB,
    StudentAccountLink,
    StudentRecord,
    TeacherStudentLink,
    User,
)

router = APIRouter(prefix="/api/v1", tags=["school"])


def _linked_student_ids(current_user: User, db: Session) -> list[str] | None:
    if current_user.role == UserRole.DIRECTIVO.value:
        return None
    if current_user.role == UserRole.DOCENTE.value:
        assigned_grades = [
            assignment.grade
            for assignment in db.query(CourseTeacherAssignment)
            .filter(CourseTeacherAssignment.teacher_id == current_user.id)
            .all()
        ]
        if assigned_grades:
            return sorted(
                student.student_id
                for student in db.query(StudentRecord)
                .filter(StudentRecord.grade.in_(assigned_grades))
                .all()
            )
        return [
            link.student_id
            for link in db.query(TeacherStudentLink)
            .filter(TeacherStudentLink.user_id == current_user.id)
            .all()
        ]
    elif current_user.role == UserRole.ACUDIENTE.value:
        link_model = GuardianStudentLink
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return [link.student_id for link in db.query(link_model).filter(link_model.user_id == current_user.id).all()]


def _require_student_access(student_id: str, current_user: User, db: Session) -> None:
    linked_ids = _linked_student_ids(current_user, db)
    if linked_ids is not None and student_id not in linked_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student is not assigned to this account")


def _require_course_subject(
    student_id: str,
    subject: str | None,
    current_user: User,
    db: Session,
) -> None:
    if current_user.role != UserRole.DOCENTE.value:
        return
    student = db.query(StudentRecord).filter(StudentRecord.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    course_has_assignments = (
        db.query(CourseTeacherAssignment)
        .filter(CourseTeacherAssignment.grade == student.grade)
        .first()
        is not None
    )
    assignment_query = db.query(CourseTeacherAssignment).filter(
        CourseTeacherAssignment.grade == student.grade,
        CourseTeacherAssignment.teacher_id == current_user.id,
    )
    if subject is not None:
        assignment_query = assignment_query.filter(CourseTeacherAssignment.subject == subject)
    if course_has_assignments and assignment_query.first() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this subject or course")


@router.post("/students")
def create_student(student: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing = db.query(StudentRecord).filter(StudentRecord.student_id == student["student_id"]).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student already exists")
    if student.get("grade") not in {str(grade) for grade in range(6, 12)}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Grade must be between 6 and 11")

    account_email = student.get("account_email")
    account_password = student.get("account_password")
    if bool(account_email) != bool(account_password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account email and password are both required")
    if account_email:
        if "@" not in account_email or len(account_password) < 8:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide a valid email and a password of at least 8 characters")
        if db.query(User).filter(User.email == account_email).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    record = StudentRecord(
        student_id=student["student_id"],
        full_name=student["full_name"],
        document_number=student["document_number"],
        grade=student.get("grade"),
        status=student.get("status", "ACTIVE"),
    )
    db.add(record)
    db.flush()
    if account_email:
        account = User(
            email=account_email,
            full_name=record.full_name,
            password_hash=get_password_hash(account_password),
            role=UserRole.ESTUDIANTE.value,
        )
        db.add(account)
        db.flush()
        db.add(StudentAccountLink(user_id=account.id, student_id=record.student_id))
    db.commit()
    db.refresh(record)
    return record


@router.patch("/students/{student_id}")
def update_student(
    student_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    student = db.query(StudentRecord).filter(StudentRecord.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if "full_name" in payload:
        full_name = payload["full_name"].strip()
        if not full_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Student name cannot be empty")
        student.full_name = full_name
        account_link = db.query(StudentAccountLink).filter(StudentAccountLink.student_id == student_id).first()
        if account_link:
            student_user = db.query(User).filter(User.id == account_link.user_id).first()
            if student_user:
                student_user.full_name = full_name
    if "grade" in payload:
        grade = payload["grade"]
        if grade not in {str(value) for value in range(6, 12)}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Grade must be between 6 and 11")
        student.grade = grade
    db.commit()
    db.refresh(student)
    return student


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    student = db.query(StudentRecord).filter(StudentRecord.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    account_link = db.query(StudentAccountLink).filter(StudentAccountLink.student_id == student_id).first()
    if account_link:
        student_user = db.query(User).filter(User.id == account_link.user_id).first()
        db.delete(account_link)
        if student_user:
            db.delete(student_user)
    for model in (AttendanceRecord, GradeRecord, ObserverRecordDB, TeacherStudentLink, GuardianStudentLink):
        db.query(model).filter(model.student_id == student_id).delete(synchronize_session=False)
    db.delete(student)
    db.commit()


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    role = payload.get("role")
    if role not in {UserRole.DOCENTE.value, UserRole.ACUDIENTE.value}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Role must be DOCENTE or ACUDIENTE")

    email = payload.get("email", "").strip().lower()
    full_name = payload.get("full_name", "").strip()
    password = payload.get("password", "")
    student_id = payload.get("student_id") or None
    if "@" not in email or not full_name or len(password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide a valid email, name, and password of at least 8 characters")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    if student_id and db.query(StudentRecord).filter(StudentRecord.student_id == student_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    account = User(
        email=email,
        full_name=full_name,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(account)
    db.flush()
    if student_id:
        link_model = TeacherStudentLink if role == UserRole.DOCENTE.value else GuardianStudentLink
        db.add(link_model(user_id=account.id, student_id=student_id))
    db.commit()
    return {"id": account.id, "email": account.email, "full_name": account.full_name, "role": account.role}


@router.get("/students")
def list_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value, UserRole.ACUDIENTE.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    linked_ids = _linked_student_ids(current_user, db)
    query = db.query(StudentRecord)
    if linked_ids is not None:
        query = query.filter(StudentRecord.student_id.in_(linked_ids))
    return query.all()


@router.post("/assignments")
def assign_student(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DIRECTIVO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    email = payload.get("email")
    student_id = payload.get("student_id")
    assigned_user = db.query(User).filter(User.email == email).first()
    if assigned_user is None or db.query(StudentRecord).filter(StudentRecord.student_id == student_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or student not found")

    link_model = {
        UserRole.DOCENTE.value: TeacherStudentLink,
        UserRole.ACUDIENTE.value: GuardianStudentLink,
    }.get(assigned_user.role)
    if link_model is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only teachers and guardians can be assigned")

    link = (
        db.query(link_model)
        .filter(link_model.user_id == assigned_user.id, link_model.student_id == student_id)
        .first()
    )
    if link is None:
        db.add(link_model(user_id=assigned_user.id, student_id=student_id))
        db.commit()
    return {"status": "ok", "email": email, "student_id": student_id, "role": assigned_user.role}


@router.post("/attendance")
def register_attendance(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _require_student_access(payload["student_id"], current_user, db)

    attendance = AttendanceRecord(
        student_id=payload["student_id"],
        attendance_date=payload["attendance_date"],
        present=payload["present"],
        justification=payload.get("justification"),
        noted_by=current_user.email,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/attendance/{student_id}")
def get_student_attendance(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value, UserRole.ACUDIENTE.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _require_student_access(student_id, current_user, db)

    records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id).all()
    return records


@router.post("/grades")
def register_grade(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _require_student_access(payload["student_id"], current_user, db)
    _require_course_subject(payload["student_id"], payload["subject"], current_user, db)

    record = GradeRecord(
        student_id=payload["student_id"],
        subject=payload["subject"],
        period=payload["period"],
        value=str(payload["value"]),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/grades/{student_id}")
def get_student_grades(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value, UserRole.ACUDIENTE.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _require_student_access(student_id, current_user, db)

    return db.query(GradeRecord).filter(GradeRecord.student_id == student_id).all()


@router.post("/observations")
def add_observation(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _require_student_access(payload["student_id"], current_user, db)
    _require_course_subject(payload["student_id"], None, current_user, db)

    record = ObserverRecordDB(
        student_id=payload["student_id"],
        category=payload["category"],
        description=payload["description"],
        severity=payload.get("severity", "MEDIUM"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/observations/{student_id}")
def get_student_observations(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value, UserRole.ACUDIENTE.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _require_student_access(student_id, current_user, db)

    return db.query(ObserverRecordDB).filter(ObserverRecordDB.student_id == student_id).all()


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.DOCENTE.value, UserRole.DIRECTIVO.value, UserRole.ACUDIENTE.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    linked_ids = _linked_student_ids(current_user, db)
    students_query = db.query(StudentRecord)
    attendance_query = db.query(AttendanceRecord)
    grades_query = db.query(GradeRecord)
    observations_query = db.query(ObserverRecordDB)
    if linked_ids is not None:
        students_query = students_query.filter(StudentRecord.student_id.in_(linked_ids))
        attendance_query = attendance_query.filter(AttendanceRecord.student_id.in_(linked_ids))
        grades_query = grades_query.filter(GradeRecord.student_id.in_(linked_ids))
        observations_query = observations_query.filter(ObserverRecordDB.student_id.in_(linked_ids))
    students = students_query.all()
    return {
        "total_students": len(students),
        "active_students": sum(1 for s in students if s.status == "ACTIVE"),
        "attendance_records": attendance_query.count(),
        "grades_records": grades_query.count(),
        "observer_records": observations_query.count(),
    }
