"""
Integration tests for the Scans API using FastAPI's TestClient with an
isolated in-memory SQLite database (does not touch the dev hata.db).
"""
import sys
import io
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)

# Authenticate once and attach the token to every request in this suite,
# matching how the real frontend behaves once logged in.
_login_resp = client.post("/api/auth/login", json={"password": "operationhata"})
_token = _login_resp.json()["token"]
client.headers.update({"Authorization": f"Bearer {_token}"})


def _make_jpeg_bytes():
    img = Image.new("RGB", (50, 50), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_login_rejects_wrong_password():
    resp = client.post("/api/auth/login", json={"password": "wrong-password"})
    assert resp.status_code == 401


def test_login_accepts_correct_password():
    resp = client.post("/api/auth/login", json={"password": "operationhata"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_protected_endpoint_rejects_missing_token():
    unauthenticated = TestClient(app)
    resp = unauthenticated.get("/api/dashboard/stats")
    assert resp.status_code == 401


def test_upload_valid_image():
    files = {"file": ("test.jpg", _make_jpeg_bytes(), "image/jpeg")}
    resp = client.post("/api/scans/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["detected_format"] == "JPEG"
    assert "scan_id" in data


def test_upload_rejects_non_image():
    files = {"file": ("test.jpg", b"this is not an image", "image/jpeg")}
    resp = client.post("/api/scans/upload", files=files)
    assert resp.status_code == 400


def test_upload_rejects_unsupported_extension():
    files = {"file": ("test.txt", b"hello", "text/plain")}
    resp = client.post("/api/scans/upload", files=files)
    assert resp.status_code == 400


def test_upload_rejects_empty_file():
    files = {"file": ("test.jpg", b"", "image/jpeg")}
    resp = client.post("/api/scans/upload", files=files)
    assert resp.status_code == 400


def test_full_scan_lifecycle():
    files = {"file": ("lifecycle.jpg", _make_jpeg_bytes(), "image/jpeg")}
    upload_resp = client.post("/api/scans/upload", files=files)
    scan_id = upload_resp.json()["scan_id"]

    start_resp = client.post(f"/api/scans/{scan_id}/start")
    assert start_resp.status_code == 200

    get_resp = client.get(f"/api/scans/{scan_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["scan"]["id"] == scan_id


def test_get_nonexistent_scan_returns_404():
    resp = client.get("/api/scans/HATA-DOESNOTEXIST")
    assert resp.status_code == 404


def test_dashboard_stats_endpoint():
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scanned" in data
    assert "distribution" in data


def test_quarantine_delete_requires_confirmation():
    resp = client.request("DELETE", "/api/quarantine/QTN-FAKE", json={"confirm": False})
    assert resp.status_code == 400


def test_email_status_when_not_connected():
    resp = client.get("/api/emails/status")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


def test_settings_get_and_update():
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    update_resp = client.post("/api/settings", json={"notifications_enabled": False})
    assert update_resp.status_code == 200
    assert update_resp.json()["notifications_enabled"] is False
