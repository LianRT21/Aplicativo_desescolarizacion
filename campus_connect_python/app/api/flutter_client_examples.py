from __future__ import annotations

# Este archivo sirve como referencia para consumir la API desde Flutter.
# No es parte de la ejecución del backend, solo guía de integración.

EXAMPLES = {
    "login": {
        "url": "/api/v1/auth/login",
        "method": "POST",
        "body": {
            "username": "teacher@campus.com",
            "password": "teacher123",
        },
    },
    "dashboard": {
        "url": "/api/v1/dashboard",
        "method": "GET",
        "headers": {
            "Authorization": "Bearer TOKEN_AQUI",
        },
    },
    "create_student": {
        "url": "/api/v1/students",
        "method": "POST",
        "body": {
            "student_id": "stu-001",
            "full_name": "Ana Gómez",
            "document_number": "1012345678",
            "grade": "11A",
            "status": "ACTIVE",
        },
    },
    "attendance": {
        "url": "/api/v1/attendance",
        "method": "POST",
        "body": {
            "student_id": "stu-001",
            "attendance_date": "2026-09-09",
            "present": False,
            "justification": "Cita médica",
        },
    },
    "grades": {
        "url": "/api/v1/grades",
        "method": "POST",
        "body": {
            "student_id": "stu-001",
            "subject": "Matemáticas",
            "period": "Corte 1",
            "value": 4.2,
        },
    },
    "risk": {
        "url": "/api/v1/risk/evaluate",
        "method": "POST",
        "body": {
            "id": "stu-001",
            "full_name": "Ana Gómez",
            "document_number": "1012345678",
            "grade": "11A",
            "status": "ACTIVE",
            "attendance_records": [
                {"student_id": "stu-001", "date": "2026-09-01", "present": False},
                {"student_id": "stu-001", "date": "2026-09-02", "present": False},
                {"student_id": "stu-001", "date": "2026-09-03", "present": False},
            ],
            "grades": [
                {"student_id": "stu-001", "subject": "Matemáticas", "period": "Corte 1", "value": 2.8},
            ],
            "observer_records": [
                {"student_id": "stu-001", "category": "Familiar/Entorno", "description": "Sin apoyo familiar", "severity": "MEDIUM"},
            ],
            "absent_parent_meetings": 1,
            "warnings_this_month": 2,
        },
    },
}

# Ejemplo de uso con Dart/Flutter (conceptual):
#
# final response = await http.post(
#   Uri.parse('http://localhost:8000/api/v1/auth/login'),
#   headers: {'Content-Type': 'application/x-www-form-urlencoded'},
#   body: {'username': 'teacher@campus.com', 'password': 'teacher123'},
# );
#
# final token = jsonDecode(response.body)['access_token'];
