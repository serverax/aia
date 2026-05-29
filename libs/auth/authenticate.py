import os
from typing import Optional

from .models import UserInDB
from .security import get_password_hash, verify_password

# True while the only identity store is the in-memory dict below. Flip to False
# (and wire a DB-backed store) when real users land. Used by the production guard.
USING_FAKE_USER_DB = True
_DEV_DEFAULT_SECRET = "super-secret-key-for-dev-only"


def assert_auth_safe_for_production() -> None:
    """Refuse dev-only auth in a production environment.

    Production (``AIA_ENV`` in {prod, production}) must NOT rely on the in-memory
    ``fake_users_db`` or the dev-default JWT secret. Set ``AIA_ALLOW_DEV_AUTH=true``
    to explicitly override (e.g. a controlled staging smoke test). Raises
    ``RuntimeError`` otherwise so the service fails loudly instead of shipping
    fake identities.
    """
    env = os.environ.get("AIA_ENV", "dev").strip().lower()
    if env not in {"prod", "production"}:
        return
    if os.environ.get("AIA_ALLOW_DEV_AUTH", "").strip().lower() in {"1", "true", "yes"}:
        return
    from .security import SECRET_KEY

    problems = []
    if USING_FAKE_USER_DB:
        problems.append("in-memory fake_users_db (no DB-backed users)")
    if SECRET_KEY == _DEV_DEFAULT_SECRET:
        problems.append("dev-default AIA_AUTH_SECRET_KEY")
    if problems:
        raise RuntimeError(
            f"Refusing dev-only auth in production (AIA_ENV={env}): {'; '.join(problems)}. "
            "Provide a DB-backed user store and a real AIA_AUTH_SECRET_KEY, or set "
            "AIA_ALLOW_DEV_AUTH=true to override."
        )


# Mock user database (dev only — see USING_FAKE_USER_DB / assert_auth_safe_for_production)
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
