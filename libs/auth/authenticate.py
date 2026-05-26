from typing import Optional

from .models import UserInDB
from .security import get_password_hash, verify_password

# Mock user database
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@ordinoxai.com",
        "hashed_password": get_password_hash("synthetic-admin-secret"),
        "disabled": False,
        "scopes": ["me", "items", "admin"],
    },
    "analyst": {
        "username": "analyst",
        "full_name": "Senior Analyst",
        "email": "analyst@ordinoxai.com",
        "hashed_password": get_password_hash("analyst-dev-pass"),
        "disabled": False,
        "scopes": ["me", "items"],
    },
}


async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user_dict = fake_users_db.get(username)
    if not user_dict:
        return None
    user = UserInDB(**user_dict)
    if not verify_password(password, user.hashed_password):
        return None
    return user
