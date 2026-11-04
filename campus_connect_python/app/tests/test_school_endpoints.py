import uuid

from fastapi.testclient import TestClient

from app.api.main import app
from app.core.database import SessionLocal
from app.db.models import StudentRecord, User
from app.core.security import get_password_hash, verify_password


client = TestClient(app)


def test_school_dashboard_requires_authentication():
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401


def test_teacher_can_login_and_access_dashboard():
    db = SessionLocal()
    existed = db.query(User).filter(User.email == "teacher@campus.com").first()
    if existed is None:
        db.add(User(email="teacher@campus.com", full_name="Teacher Campus", password_hash=get_password_hash("teacher123"), role="DOCENTE"))
        db.commit()
    db.close()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "teacher@campus.com", "password": "teacher123"},
    )
    token = login.json()["access_token"]

    dashboard = client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "total_students" in body


def test_guardian_and_teacher_are_scoped_to_linked_students():
    client.post("/api/v1/auth/seed")
    db = SessionLocal()
    outside_student_id = "unlinked-student"
    if db.query(StudentRecord).filter(StudentRecord.student_id == outside_student_id).first() is None:
        db.add(
            StudentRecord(
                student_id=outside_student_id,
                full_name="Unlinked Student",
                document_number="9999999999",
                grade="10",
            )
        )
        db.commit()
    db.close()

    guardian_login = client.post(
        "/api/v1/auth/login",
        data={"username": "parent@campus.com", "password": "parent123"},
    )
    guardian_headers = {"Authorization": f"Bearer {guardian_login.json()['access_token']}"}
    guardian_students = client.get("/api/v1/students", headers=guardian_headers)
    assert guardian_students.status_code == 200
    guardian_student_ids = {student["student_id"] for student in guardian_students.json()}
    assert "stu-diego-001" in guardian_student_ids
    assert outside_student_id not in guardian_student_ids
    assert client.get(f"/api/v1/attendance/{outside_student_id}", headers=guardian_headers).status_code == 403
    assert client.get("/api/v1/attendance/stu-diego-001", headers=guardian_headers).status_code == 200

    teacher_login = client.post(
        "/api/v1/auth/login",
        data={"username": "teacher@campus.com", "password": "teacher123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    attendance = client.post(
        "/api/v1/attendance",
        json={"student_id": outside_student_id, "attendance_date": "2026-11-03", "present": True},
        headers=teacher_headers,
    )
    assert attendance.status_code == 403
    assigned_attendance = client.post(
        "/api/v1/attendance",
        json={"student_id": "stu-diego-001", "attendance_date": "2026-11-03", "present": True},
        headers=teacher_headers,
    )
    assert assigned_attendance.status_code == 200


def test_director_can_create_and_assign_students():
    client.post("/api/v1/auth/seed")
    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    director_headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}
    existing_students = client.get("/api/v1/students", headers=director_headers).json()
    if "new-assigned-student" not in {student["student_id"] for student in existing_students}:
        create_response = client.post(
            "/api/v1/students",
            json={
                "student_id": "new-assigned-student",
                "full_name": "New Assigned Student",
                "document_number": "8888888888",
                "grade": "9",
            },
            headers=director_headers,
        )
        assert create_response.status_code == 200

    assignment = client.post(
        "/api/v1/assignments",
        json={"email": "parent@campus.com", "student_id": "new-assigned-student"},
        headers=director_headers,
    )
    assert assignment.status_code == 200

    parent_login = client.post(
        "/api/v1/auth/login",
        data={"username": "parent@campus.com", "password": "parent123"},
    )
    parent_headers = {"Authorization": f"Bearer {parent_login.json()['access_token']}"}
    children = client.get("/api/v1/students", headers=parent_headers).json()
    assert "new-assigned-student" in {student["student_id"] for student in children}


def test_director_creates_student_with_login_account():
    client.post("/api/v1/auth/seed")
    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    director_headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}
    suffix = uuid.uuid4().hex[:8]
    student_id = f"student-{suffix}"
    email = f"student-{suffix}@campus.com"
    password = "newstudent123"

    created = client.post(
        "/api/v1/students",
        json={
            "student_id": student_id,
            "full_name": "New Student",
            "document_number": f"9{suffix}",
            "grade": "8",
            "account_email": email,
            "account_password": password,
        },
        headers=director_headers,
    )
    assert created.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "ESTUDIANTE"
    db = SessionLocal()
    account = db.query(User).filter(User.email == email).first()
    assert account is not None
    assert account.password_hash != password
    assert verify_password(password, account.password_hash)
    db.close()

    portal = client.get(
        "/api/v1/student/portal",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert portal.status_code == 200
    assert portal.json()["student"]["id"] == student_id


def test_director_creates_teacher_and_guardian_accounts():
    client.post("/api/v1/auth/seed")
    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    director_headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}

    for role, name in (("DOCENTE", "teacher"), ("ACUDIENTE", "guardian")):
        suffix = uuid.uuid4().hex[:8]
        email = f"{name}-{suffix}@campus.com"
        password = f"{name}pass123"
        created = client.post(
            "/api/v1/accounts",
            json={
                "full_name": f"New {name.title()}",
                "email": email,
                "password": password,
                "role": role,
                "student_id": "stu-diego-001",
            },
            headers=director_headers,
        )
        assert created.status_code == 201

        login = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == role
        students = client.get(
            "/api/v1/students",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        assert [student["student_id"] for student in students.json()] == ["stu-diego-001"]


def test_course_subject_rules_and_generated_schedule_have_no_conflicts():
    client.post("/api/v1/auth/seed")
    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}

    courses = client.get("/api/v1/courses", headers=headers)
    assert courses.status_code == 200
    assert {course["grade"] for course in courses.json()} == {"6", "7", "8", "9", "10", "11"}

    invalid_subject = client.post(
        "/api/v1/courses/6/assignments",
        json={"subject": "Filosofía", "teacher_email": "teacher@campus.com"},
        headers=headers,
    )
    assert invalid_subject.status_code == 422

    for grade in ("6", "7"):
        assigned = client.post(
            f"/api/v1/courses/{grade}/assignments",
            json={"subject": "Matemáticas", "teacher_email": "teacher@campus.com"},
            headers=headers,
        )
        assert assigned.status_code == 201

    second_teacher_email = f"second-teacher-{uuid.uuid4().hex[:8]}@campus.com"
    created_teacher = client.post(
        "/api/v1/accounts",
        json={
            "full_name": "Second Teacher",
            "email": second_teacher_email,
            "password": "secondpass123",
            "role": "DOCENTE",
        },
        headers=headers,
    )
    assert created_teacher.status_code == 201
    duplicate = client.post(
        "/api/v1/courses/6/assignments",
        json={"subject": "Matemáticas", "teacher_email": second_teacher_email},
        headers=headers,
    )
    assert duplicate.status_code == 409

    generated = client.post("/api/v1/courses/schedule/generate", headers=headers)
    assert generated.status_code == 200

    all_teacher_slots = []
    for grade in ("6", "7"):
        schedule = client.get(f"/api/v1/courses/{grade}/schedule", headers=headers)
        assert schedule.status_code == 200
        entries = schedule.json()
        course_slots = [(entry["weekday"], entry["period"]) for entry in entries]
        assert len(course_slots) == len(set(course_slots))
        all_teacher_slots.extend(
            (entry["teacher_id"], entry["weekday"], entry["period"]) for entry in entries
        )
    assert len(all_teacher_slots) == len(set(all_teacher_slots))


def test_director_can_delete_student_and_student_account():
    client.post("/api/v1/auth/seed")
    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}
    suffix = uuid.uuid4().hex[:8]
    student_id = f"delete-{suffix}"
    email = f"delete-{suffix}@campus.com"
    created = client.post(
        "/api/v1/students",
        json={
            "student_id": student_id,
            "full_name": "Student to Delete",
            "document_number": f"7{suffix}",
            "grade": "6",
            "account_email": email,
            "account_password": "deletepass123",
        },
        headers=headers,
    )
    assert created.status_code == 200

    removed = client.delete(f"/api/v1/students/{student_id}", headers=headers)
    assert removed.status_code == 204
    students = client.get("/api/v1/students", headers=headers).json()
    assert student_id not in {student["student_id"] for student in students}
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "deletepass123"},
    )
    assert login.status_code == 401


def test_profile_names_follow_role_permissions():
    client.post("/api/v1/auth/seed")
    teacher_login = client.post(
        "/api/v1/auth/login",
        data={"username": "teacher@campus.com", "password": "teacher123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    renamed_teacher = client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Docente Updated"},
        headers=teacher_headers,
    )
    assert renamed_teacher.status_code == 200
    assert renamed_teacher.json()["full_name"] == "Docente Updated"

    student_login = client.post(
        "/api/v1/auth/login",
        data={"username": "student@campus.com", "password": "student123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    assert client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Unauthorized Change"},
        headers=student_headers,
    ).status_code == 403

    director_login = client.post(
        "/api/v1/auth/login",
        data={"username": "director@campus.com", "password": "admin123"},
    )
    director_headers = {"Authorization": f"Bearer {director_login.json()['access_token']}"}
    renamed_student = client.patch(
        "/api/v1/students/stu-diego-001",
        json={"full_name": "Student Name Updated"},
        headers=director_headers,
    )
    assert renamed_student.status_code == 200
    portal = client.get("/api/v1/student/portal", headers=student_headers)
    assert portal.json()["student"]["full_name"] == "Student Name Updated"
