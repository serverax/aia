# Authentication & Authorization (Sprint 11)

## Overview
Synthetic Enterprise uses a JWT-based authentication and authorization system implemented in `libs/auth`.

## Configuration
- `AIA_AUTH_SECRET_KEY`: Secret key for JWT signing (default: `super-secret-key-for-dev-only`).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time (default: `60`).

## Usage

### 1. Protecting Endpoints (FastAPI)
Use the `Security` dependency from FastAPI with `get_current_active_user` and required `scopes`.

```python
from fastapi import Security
from libs.auth import get_current_active_user, User

@app.post("/protected")
async def protected_endpoint(
    current_user: User = Security(get_current_active_user, scopes=["items"])
):
    return {"message": "You are authorized!"}
```

### 2. Obtaining a Token
POST to `/token` with form data:
- `username`
- `password`
- `scopes` (optional)

### 3. Default Dev Users
| Username | Password | Scopes |
|----------|----------|--------|
| `admin` | `synthetic-admin-secret` | `me`, `items`, `admin` |
| `analyst` | `analyst-dev-pass` | `me`, `items` |

## Components
- `libs/auth/security.py`: JWT and hashing utilities.
- `libs/auth/middleware.py`: FastAPI dependencies.
- `libs/auth/models.py`: Pydantic models for User and Token.
- `libs/auth/authenticate.py`: User authentication logic (mock database for now).
