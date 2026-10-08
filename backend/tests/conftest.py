"""
Ensures test isolation: tests never touch the real development database or
the real quarantine/reports directories. Must run before any `app.*` import.
"""
import os
import tempfile

_tmp_root = tempfile.mkdtemp(prefix="hata_test_")

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["AI_API_KEY"] = ""  # force deterministic fallback report in tests
os.environ["VIRUSTOTAL_API_KEY"] = ""
