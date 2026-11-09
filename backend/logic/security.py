import base64
import hashlib
import hmac
import json
import os
import secrets
import time

# 未設定の場合は起動ごとに生成する（再起動すると既存のログインは無効になる）
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
TOKEN_TTL_SECONDS = 60 * 60 * 12
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, _, digest = stored.partition("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS).hex()
    return hmac.compare_digest(candidate, digest)


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    body = {"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    payload = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> int | None:
    payload, _, signature = token.partition(".")
    if not payload or not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        body = json.loads(base64.urlsafe_b64decode(payload.encode()))
    except ValueError:
        return None
    if body.get("exp", 0) < time.time():
        return None
    return body.get("uid")
