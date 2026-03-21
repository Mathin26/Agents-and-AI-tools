"""
auth.py — Simple user authentication (JSON-backed, bcrypt-hashed passwords).
Swap for a real database in production.
"""

from __future__ import annotations
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Optional


def _hash_password(password: str, salt: str) -> str:
    """SHA-256 + salt — replace with bcrypt in production."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


@dataclass
class User:
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    created_at: float = field(default_factory=time.time)
    api_key_hint: str = ""  # last 4 chars of user's Anthropic key

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "User":
        return cls(**d)

    def check_password(self, password: str) -> bool:
        return _hash_password(password, self.salt) == self.password_hash


@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)  # 24h

    def is_valid(self) -> bool:
        return time.time() < self.expires_at

    def to_dict(self) -> Dict:
        return asdict(self)


class UserAuth:
    """
    Simple file-backed user auth system.

    Usage:
        auth = UserAuth(data_dir="./auth_data")
        user = auth.register("alice", "alice@example.com", "secret123")
        session = auth.login("alice", "secret123")
        user = auth.get_session_user(session.session_id)
    """

    def __init__(self, data_dir: str = "./auth_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._users_path = self.data_dir / "users.json"
        self._sessions_path = self.data_dir / "sessions.json"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_users(self) -> Dict[str, Dict]:
        if self._users_path.exists():
            return json.loads(self._users_path.read_text())
        return {}

    def _save_users(self, users: Dict[str, Dict]) -> None:
        self._users_path.write_text(json.dumps(users, indent=2))

    def _load_sessions(self) -> Dict[str, Dict]:
        if self._sessions_path.exists():
            return json.loads(self._sessions_path.read_text())
        return {}

    def _save_sessions(self, sessions: Dict[str, Dict]) -> None:
        self._sessions_path.write_text(json.dumps(sessions, indent=2))

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def register(
        self,
        username: str,
        email: str,
        password: str,
        api_key_hint: str = "",
    ) -> User:
        """Register a new user. Raises ValueError if username already exists."""
        users = self._load_users()
        if username in users:
            raise ValueError(f"Username '{username}' is already taken.")
        # Check email uniqueness
        for u in users.values():
            if u["email"] == email:
                raise ValueError(f"Email '{email}' is already registered.")

        salt = secrets.token_hex(16)
        user = User(
            user_id=secrets.token_hex(12),
            username=username,
            email=email,
            password_hash=_hash_password(password, salt),
            salt=salt,
            api_key_hint=api_key_hint[-4:] if api_key_hint else "",
        )
        users[username] = user.to_dict()
        self._save_users(users)
        return user

    def get_user(self, username: str) -> Optional[User]:
        users = self._load_users()
        d = users.get(username)
        return User.from_dict(d) if d else None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        for u in self._load_users().values():
            if u["user_id"] == user_id:
                return User.from_dict(u)
        return None

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> Session:
        """Authenticate and return a session. Raises ValueError on failure."""
        user = self.get_user(username)
        if not user or not user.check_password(password):
            raise ValueError("Invalid username or password.")

        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user.user_id,
        )
        sessions = self._load_sessions()
        sessions[session.session_id] = session.to_dict()
        self._save_sessions(sessions)
        return session

    def logout(self, session_id: str) -> None:
        sessions = self._load_sessions()
        sessions.pop(session_id, None)
        self._save_sessions(sessions)

    def get_session_user(self, session_id: str) -> Optional[User]:
        """Return the User associated with a session, or None if invalid/expired."""
        sessions = self._load_sessions()
        sd = sessions.get(session_id)
        if not sd:
            return None
        session = Session(**sd)
        if not session.is_valid():
            sessions.pop(session_id, None)
            self._save_sessions(sessions)
            return None
        return self.get_user_by_id(session.user_id)
