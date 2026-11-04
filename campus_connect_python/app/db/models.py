from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="DOCENTE")
    is_active = Column(Boolean, default=True)


class StudentRecord(Base):
    __tablename__ = "student_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=False)
    document_number = Column(String, nullable=False)
    grade = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE")


class StudentAccountLink(Base):
    __tablename__ = "student_account_links"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    student_id = Column(String, ForeignKey("student_records.student_id"), unique=True, nullable=False)


class TeacherStudentLink(Base):
    __tablename__ = "teacher_student_links"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    student_id = Column(String, ForeignKey("student_records.student_id"), primary_key=True)


class GuardianStudentLink(Base):
    __tablename__ = "guardian_student_links"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    student_id = Column(String, ForeignKey("student_records.student_id"), primary_key=True)


class CourseTeacherAssignment(Base):
    __tablename__ = "course_teacher_assignments"
    __table_args__ = (UniqueConstraint("grade", "subject", name="uq_course_subject_teacher"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    grade = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint("grade", "weekday", "period", name="uq_course_schedule_slot"),
        UniqueConstraint("teacher_id", "weekday", "period", name="uq_teacher_schedule_slot"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    grade = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    starts_at = Column(String, nullable=False)
    ends_at = Column(String, nullable=False)


class CourseItem(Base):
    __tablename__ = "course_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    grade = Column(String, nullable=False, index=True)
    item_type = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    event_date = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, nullable=False, index=True)
    attendance_date = Column(String, nullable=False)
    present = Column(Boolean, nullable=False)
    justification = Column(Text, nullable=True)
    noted_by = Column(String, nullable=True)


class GradeRecord(Base):
    __tablename__ = "grade_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    period = Column(String, nullable=False)
    value = Column(String, nullable=False)


class ObserverRecordDB(Base):
    __tablename__ = "observer_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False, default="MEDIUM")
