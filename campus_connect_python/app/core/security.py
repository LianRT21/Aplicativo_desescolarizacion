from __future__ import annotations

import hashlib
import hmac
import os
from enum import Enum
from typing import Any, Dict, List


class UserRole(str, Enum):
    DOCENTE = "DOCENTE"
    ACUDIENTE = "ACUDIENTE"
    DIRECTIVO = "DIRECTIVO"
    ESTUDIANTE = "ESTUDIANTE"


def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if ":" not in hashed_password:
        return False

    salt_hex, digest_hex = hashed_password.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000).hex()
    return hmac.compare_digest(expected, digest_hex)


ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
    UserRole.DOCENTE: [
        "attendance:read",
        "attendance:write",
        "grades:read",
        "grades:write",
        "observer:read",
        "observer:write",
    ],
    UserRole.ACUDIENTE: [
        "student:read",
        "grades:read",
        "attendance:read",
        "alerts:read",
    ],
    UserRole.DIRECTIVO: [
        "student:read",
        "student:write",
        "grades:read",
        "attendance:read",
        "alerts:read",
        "alerts:write",
        "report:read",
    ],
}


class AuthContext:
    def __init__(self, user_id: str, role: UserRole, school_id: str | None = None):
        self.user_id = user_id
        self.role = role
        self.school_id = school_id

    def has_permission(self, permission: str) -> bool:
        return permission in ROLE_PERMISSIONS.get(self.role, [])


def require_role(*allowed_roles: UserRole):
    def decorator(func):
        def wrapper(*args, **kwargs):
            auth: AuthContext | None = kwargs.get("auth")
            if auth is None:
                for value in args[1:]:
                    if isinstance(value, AuthContext):
                        auth = value
                        break
            if auth is None:
                raise PermissionError("Authentication context is required")
            if auth.role not in allowed_roles:
                raise PermissionError(f"Role {auth.role.value} is not allowed for this action")
            return func(*args, **kwargs)

        return wrapper

    return decorator
