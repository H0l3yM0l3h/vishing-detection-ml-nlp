"""
Automated security tests for the ShieldGuard API.
=================================================
These implement the security cases specified in testing.md (ST-001 .. ST-015),
which were written up as a manual test plan and never automated. Each test
names the control it asserts, so a failure says which defence regressed rather
than only which line broke.

They run against the real FastAPI application with a fake database, so the
routes, dependencies, middleware and error handlers under test are the same
code that is deployed.
"""

import pytest

from conftest import ADMIN_USER, TEST_PASSWORD, TEST_USER

pytestmark = [pytest.mark.security, pytest.mark.unit]


# ══════════════════════════════════════════════════════════════
# Password policy and hashing  (ST-001, ST-002)
# ══════════════════════════════════════════════════════════════

class TestPasswordPolicy:
    def test_rejects_password_under_twelve_characters(self):
        from auth import validate_password

        ok, reason = validate_password("Short1!")
        assert ok is False
        assert "12 characters" in reason

    @pytest.mark.parametrize(
        "password,missing",
        [
            ("alllowercase1!", "uppercase"),
            ("ALLUPPERCASE1!", "lowercase"),
            ("NoDigitsHere!!", "number"),
            ("NoSymbolsHere1", "special"),
        ],
    )
    def test_requires_every_character_class(self, password, missing):
        from auth import validate_password

        ok, reason = validate_password(password)
        assert ok is False
        assert missing in reason.lower()

    def test_accepts_a_compliant_password(self):
        from auth import validate_password

        assert validate_password("ProperPassw0rd!")[0] is True

    def test_password_is_hashed_not_stored(self):
        """bcrypt, salted — the same password must not produce the same hash."""
        from auth import hash_password, verify_password

        first = hash_password(TEST_PASSWORD)
        second = hash_password(TEST_PASSWORD)

        assert first != second, "identical hashes indicate a missing salt"
        assert TEST_PASSWORD.encode() not in first
        assert verify_password(TEST_PASSWORD, first)
        assert verify_password(TEST_PASSWORD, second)
        assert not verify_password("WrongPassword1!", first)


# ══════════════════════════════════════════════════════════════
# Input sanitisation  (ST-007)
# ══════════════════════════════════════════════════════════════

class TestSanitisation:
    @pytest.mark.parametrize(
        "payload",
        [
            "<script>alert(1)</script>",
            "&lt;img src=x onerror=alert(1)&gt;",          # entity-encoded
            "&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;",  # double-encoded
            "<iframe src='evil'></iframe>",
            "<svg/onload=alert(1)>",
        ],
    )
    def test_markup_never_survives_sanitisation(self, payload):
        """Regression test for the decode-after-strip ordering bug.

        sanitize_input used to strip tags and THEN unescape entities, so an
        entity-encoded payload passed through untouched and was decoded back
        into live markup afterwards.
        """
        from auth import sanitize_input

        cleaned = sanitize_input(payload)
        assert "<" not in cleaned or ">" not in cleaned, f"markup survived: {cleaned!r}"

    def test_length_is_capped(self):
        from auth import sanitize_input

        assert len(sanitize_input("a" * 50_000, 10_000)) == 10_000

    def test_non_string_input_is_rejected_safely(self):
        from auth import sanitize_input

        assert sanitize_input(None) == ""
        assert sanitize_input(12345) == ""


# ══════════════════════════════════════════════════════════════
# Authentication  (ST-003, ST-004)
# ══════════════════════════════════════════════════════════════

class TestAuthentication:
    def test_login_succeeds_and_issues_both_tokens(self, client):
        res = client.post("/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
        assert res.status_code == 200
        body = res.json()
        assert body["token"] and body["refresh_token"]
        assert body["role"] == "user"

    def test_login_failure_message_is_uniform(self, client):
        """Must not distinguish 'no such user' from 'wrong password'."""
        unknown = client.post(
            "/api/auth/login", json={"username": "no_such_account", "password": "Whatever1!"}
        )
        wrong_pw = client.post(
            "/api/auth/login", json={"username": TEST_USER, "password": "WrongPassword1!"}
        )
        assert unknown.status_code == wrong_pw.status_code == 401
        assert unknown.json()["detail"] == wrong_pw.json()["detail"]

    def test_login_does_not_disclose_remaining_attempts(self, client):
        """Telling an attacker how many tries remain hands them a budget."""
        res = client.post(
            "/api/auth/login", json={"username": TEST_USER, "password": "WrongPassword1!"}
        )
        assert "remaining_attempts" not in res.json()

    def test_protected_route_requires_a_token(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_garbage_token_is_rejected(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
        assert res.status_code == 401

    def test_token_signed_with_another_key_is_rejected(self, client):
        """The core defence against a forged admin token."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        forged = jwt.encode(
            {
                "sub": "attacker",
                "role": "admin",
                "jti": "forged",
                "typ": "access",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "change-me-in-production",   # the old hardcoded fallback
            algorithm="HS256",
        )
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert res.status_code == 401

    def test_refresh_token_cannot_authorise_a_normal_request(self, client):
        login = client.post(
            "/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD}
        ).json()
        res = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {login['refresh_token']}"}
        )
        assert res.status_code == 401


# ══════════════════════════════════════════════════════════════
# Session lifecycle  (ST-005)
# ══════════════════════════════════════════════════════════════

class TestSessionLifecycle:
    def test_logout_revokes_the_token(self, client):
        login = client.post(
            "/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD}
        ).json()
        headers = {"Authorization": f"Bearer {login['token']}"}

        assert client.get("/api/auth/me", headers=headers).status_code == 200
        client.post("/api/auth/logout", headers=headers)
        assert client.get("/api/auth/me", headers=headers).status_code == 401

    def test_refresh_rotates_and_revokes_the_previous_token(self, client):
        login = client.post(
            "/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD}
        ).json()
        old_refresh = login["refresh_token"]

        first = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert first.status_code == 200
        assert first.json()["refresh_token"] != old_refresh

        replay = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401, "a used refresh token must not work twice"


# ══════════════════════════════════════════════════════════════
# Authorisation  (ST-006)
# ══════════════════════════════════════════════════════════════

class TestAuthorisation:
    def test_analytics_is_forbidden_for_a_normal_user(self, client, auth_headers):
        assert client.get("/api/analytics", headers=auth_headers).status_code == 403

    def test_analytics_is_allowed_for_an_admin(self, client, admin_headers):
        assert client.get("/api/analytics", headers=admin_headers).status_code == 200

    def test_analytics_requires_authentication(self, client):
        assert client.get("/api/analytics").status_code == 401

    def test_history_is_scoped_to_the_caller(self, client, auth_headers, fake_db):
        fake_db.audit_log = [
            {"username": TEST_USER, "verdict": "safe"},
            {"username": ADMIN_USER, "verdict": "vishing"},
        ]
        rows = client.get("/api/history", headers=auth_headers).json()["history"]
        assert all(r["username"] == TEST_USER for r in rows)


# ══════════════════════════════════════════════════════════════
# Credential exposure  (ST-011)
# ══════════════════════════════════════════════════════════════

class TestSecretExposure:
    def test_third_party_api_key_endpoint_is_gone(self, client, auth_headers):
        """GET /api/threat-intel/key handed the PenipuMY key to the browser."""
        assert client.get("/api/threat-intel/key", headers=auth_headers).status_code == 404

    def test_error_responses_do_not_leak_exception_text(self, client, auth_headers, fake_db):
        fake_db.fail_next = True
        res = client.get("/api/history", headers=auth_headers)
        assert res.status_code == 503
        body = res.text.lower()
        for leak in ("traceback", "supabase", "postgrest", 'file "', "line "):
            assert leak not in body, f"response leaked {leak!r}"


# ══════════════════════════════════════════════════════════════
# Security headers  (ST-013)
# ══════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    @pytest.mark.parametrize(
        "header,expected",
        [
            ("content-security-policy", "frame-ancestors 'none'"),
            ("x-content-type-options", "nosniff"),
            ("x-frame-options", "DENY"),
            ("referrer-policy", "no-referrer"),
        ],
    )
    def test_defensive_headers_are_present(self, client, header, expected):
        res = client.get("/api/health")
        assert header in {k.lower() for k in res.headers}
        assert expected.lower() in res.headers[header].lower()

    def test_every_response_carries_a_request_id(self, client):
        """Needed to correlate a user-visible error with a server log line."""
        assert client.get("/api/health").headers.get("x-request-id")


# ══════════════════════════════════════════════════════════════
# Rate limiting  (ST-010)
# ══════════════════════════════════════════════════════════════

class TestRateLimiting:
    def test_repeated_login_attempts_are_throttled(self, client):
        statuses = [
            client.post(
                "/api/auth/login",
                json={"username": f"probe_{i}", "password": "Whatever1!"},
            ).status_code
            for i in range(15)
        ]
        assert 429 in statuses, "per-IP login throttle did not engage"

    def test_throttled_response_tells_the_client_when_to_retry(self, client):
        last = None
        for i in range(15):
            last = client.post(
                "/api/auth/login", json={"username": f"probe_{i}", "password": "Whatever1!"}
            )
            if last.status_code == 429:
                break
        assert last.status_code == 429
        assert last.headers.get("retry-after")


# ══════════════════════════════════════════════════════════════
# Upload handling  (ST-009)
# ══════════════════════════════════════════════════════════════

class TestUploadValidation:
    def test_disallowed_extension_is_rejected(self, client, auth_headers):
        res = client.post(
            "/api/transcribe",
            headers=auth_headers,
            files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
        assert res.status_code == 400

    def test_content_must_match_the_claimed_audio_format(self, client, auth_headers):
        """Extension alone is attacker-controlled metadata."""
        res = client.post(
            "/api/transcribe",
            headers=auth_headers,
            files={"file": ("not-really.wav", b"this is plain text, not audio", "audio/wav")},
        )
        assert res.status_code == 400

    def test_empty_upload_is_rejected(self, client, auth_headers):
        res = client.post(
            "/api/transcribe",
            headers=auth_headers,
            files={"file": ("empty.wav", b"", "audio/wav")},
        )
        assert res.status_code == 400

    def test_upload_requires_authentication(self, client):
        res = client.post(
            "/api/transcribe", files={"file": ("a.wav", b"RIFF....WAVE", "audio/wav")}
        )
        assert res.status_code == 401


# ══════════════════════════════════════════════════════════════
# Dependency failure handling
# ══════════════════════════════════════════════════════════════

class TestDatabaseFailureHandling:
    def test_database_outage_returns_503_not_500(self, client, fake_db):
        """The original defect: a DB outage surfaced as an opaque 500."""
        fake_db.fail_next = True
        res = client.post(
            "/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD}
        )
        assert res.status_code == 503
        assert res.headers.get("retry-after")
        assert res.json()["code"] == "database_unavailable"

    def test_health_endpoint_survives_a_database_outage(self, client):
        assert client.get("/api/health").status_code == 200
