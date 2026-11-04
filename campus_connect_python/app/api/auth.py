from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import UserRole, verify_password, get_password_hash
from app.db.models import (
    GuardianStudentLink,
    StudentAccountLink,
    StudentRecord,
    TeacherStudentLink,
    User,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {**data, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }


@router.patch("/me")
def update_me(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ESTUDIANTE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student names can only be changed by a director")
    full_name = (payload.get("full_name") or "").strip()
    if not full_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name cannot be empty")
    current_user.full_name = full_name
    db.commit()
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }


@router.post("/seed")
def seed_demo_users(db: Session = Depends(get_db)):
    demo_users = [
        ("director@campus.com", "Directivo Campus", "admin123", UserRole.DIRECTIVO.value),
        ("teacher@campus.com", "Docente Campus", "teacher123", UserRole.DOCENTE.value),
        ("parent@campus.com", "Acudiente Campus", "parent123", UserRole.ACUDIENTE.value),
        ("student@campus.com", "Diego Alexander López Arevalo", "student123", UserRole.ESTUDIANTE.value),
    ]

    for email, full_name, password, role in demo_users:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, full_name=full_name, password_hash=get_password_hash(password), role=role))

    student_id = "stu-diego-001"
    student = db.query(StudentRecord).filter(StudentRecord.student_id == student_id).first()
    if student is None:
        student = StudentRecord(
            student_id=student_id,
            full_name="Diego Alexander López Arevalo",
            document_number="1028481631",
            grade="11",
            status="ACTIVE",
        )
        db.add(student)
        db.flush()

    student_user = db.query(User).filter(User.email == "student@campus.com").first()
    link = db.query(StudentAccountLink).filter(StudentAccountLink.user_id == student_user.id).first()
    if link is None:
        db.add(StudentAccountLink(user_id=student_user.id, student_id=student.student_id))

    for link_model, email in (
        (TeacherStudentLink, "teacher@campus.com"),
        (GuardianStudentLink, "parent@campus.com"),
    ):
        linked_user = db.query(User).filter(User.email == email).first()
        existing_link = (
            db.query(link_model)
            .filter(link_model.user_id == linked_user.id, link_model.student_id == student.student_id)
            .first()
        )
        if existing_link is None:
            db.add(link_model(user_id=linked_user.id, student_id=student.student_id))

    db.commit()
    return {"status": "ok", "seeded_users": len(demo_users)}
