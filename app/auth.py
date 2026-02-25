import bcrypt
import re
import html


def validate_password(password: str) -> tuple:
    """
    Returns (valid: bool, reason: str).
    Enforces: 12+ chars, upper, lower, digit, special char.
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Must contain at least one number"
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/`~"\'\\]', password):
        return False, "Must contain at least one special character"
    return True, "OK"


def validate_username(username: str) -> tuple:
    """
    Returns (valid: bool, reason: str).
    Alphanumeric + underscore only, 3-32 chars.
    """
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 32:
        return False, "Username must be 32 characters or fewer"
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username may only contain letters, numbers, and underscores"
    return True, "OK"


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Strip HTML tags and limit length.
    Prevents stored XSS if transcript is ever rendered as HTML.
    """
    clean = re.sub(r"<[^>]+>", "", text)
    clean = html.unescape(clean)
    return clean[:max_length]


def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt)


def verify_password(password: str, hashed) -> bool:
    try:
        if isinstance(hashed, str):
            hashed = hashed.encode("utf-8")
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except Exception:
        return False