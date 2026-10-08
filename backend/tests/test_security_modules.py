"""
Unit tests for core security-analysis modules.
Run with: pytest tests/ -v
"""
import sys
import io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PIL import Image

from app.utils.security import (
    sanitize_filename, generate_stored_filename, detect_image_format, is_within_directory,
)
from app.services import file_signature, hash_analyzer, entropy_analyzer, risk_engine


# --------------------------------------------------------------------------
# Filename / path safety
# --------------------------------------------------------------------------

def test_sanitize_filename_strips_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("../../../evil.jpg") == "evil.jpg"


def test_sanitize_filename_strips_special_chars():
    result = sanitize_filename("my photo!@#$.jpg")
    assert " " not in result
    assert "!" not in result


def test_generate_stored_filename_is_unique():
    a = generate_stored_filename("photo.jpg")
    b = generate_stored_filename("photo.jpg")
    assert a != b
    assert a.endswith(".jpg")


def test_is_within_directory_blocks_traversal(tmp_path):
    base = tmp_path / "quarantine"
    base.mkdir()
    good = base / "scan1" / "file.jpg"
    bad = tmp_path / "outside" / "file.jpg"
    assert is_within_directory(base, good)
    assert not is_within_directory(base, bad)


# --------------------------------------------------------------------------
# File signature detection
# --------------------------------------------------------------------------

def test_detect_image_format_jpeg():
    assert detect_image_format(b"\xff\xd8\xff\xe0rest") == "JPEG"


def test_detect_image_format_png():
    assert detect_image_format(b"\x89PNG\r\n\x1a\n" + b"rest") == "PNG"


def test_detect_image_format_none_for_random_bytes():
    assert detect_image_format(b"not an image at all") is None


def test_signature_analysis_consistent(tmp_path):
    img = Image.new("RGB", (10, 10))
    path = tmp_path / "photo.jpg"
    img.save(path, "JPEG")
    result = file_signature.analyze_signature(path, "photo.jpg", "image/jpeg")
    assert result["status"] == "SAFE"
    assert result["extension_mime_consistent"] is True


def test_signature_analysis_mismatch(tmp_path):
    img = Image.new("RGB", (10, 10))
    path = tmp_path / "disguised.jpg"
    img.save(path, "PNG")  # PNG content, .jpg extension
    result = file_signature.analyze_signature(path, "disguised.jpg", "image/jpeg")
    assert result["status"] == "HIGH RISK"
    assert result["extension_mime_consistent"] is False


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------

def test_compute_hashes_deterministic(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"hello world")
    h1 = hash_analyzer.compute_hashes(path)
    h2 = hash_analyzer.compute_hashes(path)
    assert h1 == h2
    assert len(h1["sha256"]) == 64
    assert len(h1["sha1"]) == 40
    assert len(h1["md5"]) == 32


def test_virustotal_not_configured_by_default():
    result = hash_analyzer.check_virustotal_reputation("a" * 64)
    assert result["status"] == "not_configured"


# --------------------------------------------------------------------------
# Entropy
# --------------------------------------------------------------------------

def test_entropy_of_uniform_bytes_is_zero(tmp_path):
    path = tmp_path / "zeros.bin"
    path.write_bytes(b"\x00" * 5000)
    result = entropy_analyzer.analyze_entropy(path)
    assert result["overall_entropy"] == 0.0
    assert result["classification"] == "NORMAL"


def test_entropy_of_random_bytes_is_high(tmp_path):
    import os
    path = tmp_path / "random.bin"
    path.write_bytes(os.urandom(50000))
    result = entropy_analyzer.analyze_entropy(path)
    assert result["overall_entropy"] > 7.9


# --------------------------------------------------------------------------
# Risk engine
# --------------------------------------------------------------------------

def test_risk_engine_safe_file_scores_zero():
    evidence = {
        "signature": {"status": "SAFE"},
        "embedded": {"appended_data_found": False, "embedded_signatures": []},
        "yara": {"matches": []},
        "stego": {"classification": "NOT DETECTED"},
        "metadata": {"anomaly_detected": False, "anomalies": []},
        "url_results": [],
        "ocr": {"suspicious_phrases": []},
        "entropy": {"classification": "NORMAL"},
    }
    result = risk_engine.calculate_risk(evidence)
    assert result["total_score"] == 0
    assert result["category"] == "SAFE"


def test_risk_engine_critical_file_with_embedded_executable():
    evidence = {
        "signature": {"status": "HIGH RISK", "details": "mismatch"},
        "embedded": {
            "appended_data_found": True,
            "embedded_signatures": [{"type": "Windows PE executable (MZ)", "offset": 100, "size": 5000, "severity": "CRITICAL"}],
        },
        "yara": {"matches": [{"rule": "Embedded_Windows_Executable", "description": "test", "severity": "CRITICAL"}]},
        "stego": {"classification": "NOT DETECTED"},
        "metadata": {"anomaly_detected": False, "anomalies": []},
        "url_results": [],
        "ocr": {"suspicious_phrases": []},
        "entropy": {"classification": "NORMAL"},
    }
    result = risk_engine.calculate_risk(evidence)
    assert result["total_score"] >= 80
    assert result["category"] == "CRITICAL"


def test_risk_engine_score_never_exceeds_100():
    evidence = {
        "signature": {"status": "HIGH RISK", "details": "mismatch"},
        "embedded": {
            "appended_data_found": True,
            "embedded_signatures": [
                {"type": "Windows PE executable (MZ)", "offset": 100, "size": 5000, "severity": "CRITICAL"},
                {"type": "ELF executable", "offset": 200, "size": 5000, "severity": "CRITICAL"},
            ],
        },
        "yara": {"matches": [
            {"rule": "R1", "description": "d", "severity": "CRITICAL"},
            {"rule": "R2", "description": "d", "severity": "HIGH"},
        ]},
        "stego": {"classification": "HIGHLY SUSPICIOUS"},
        "metadata": {"anomaly_detected": True, "anomalies": [{"finding": "x", "severity": "high"}] * 5},
        "url_results": [{"source": "qr", "risk_level": "HIGH", "url": "http://1.2.3.4/x", "indicators": ["ip"]}],
        "ocr": {"suspicious_phrases": ["urgent", "password", "wire transfer"]},
        "entropy": {"classification": "HIGH", "tail_entropy": 7.99},
    }
    result = risk_engine.calculate_risk(evidence)
    assert result["total_score"] <= 100


def test_risk_engine_categorize_boundaries():
    assert risk_engine.categorize(0) == "SAFE"
    assert risk_engine.categorize(20) == "SAFE"
    assert risk_engine.categorize(21) == "LOW"
    assert risk_engine.categorize(40) == "LOW"
    assert risk_engine.categorize(41) == "MEDIUM"
    assert risk_engine.categorize(60) == "MEDIUM"
    assert risk_engine.categorize(61) == "HIGH"
    assert risk_engine.categorize(80) == "HIGH"
    assert risk_engine.categorize(81) == "CRITICAL"
    assert risk_engine.categorize(100) == "CRITICAL"
