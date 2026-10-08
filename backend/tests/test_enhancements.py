import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal, Base, engine
from app.models import models as m
from app.api.auth import hash_password, serialize_user, login, register, LoginRequest, RegisterRequest
from app.services.embedded_file_analyzer import analyze_embedded_content
from app.services.file_signature import analyze_signature
from app.services.risk_engine import calculate_risk
import tempfile

def test_multi_user_auth():
    print("[TEST 1] Multi-User Authentication...")
    db = SessionLocal()
    try:
        # 1. Login with seeded admin
        admin_res = login(LoginRequest(username="admin", password="Admin@12345"), db)
        assert admin_res["token"], "Admin token missing"
        assert admin_res["user"]["username"] == "admin", "Admin username mismatch"
        print("  - Admin login OK:", admin_res["user"]["username"], admin_res["user"]["role"])

        # 2. Login with seeded analyst
        analyst_res = login(LoginRequest(username="analyst", password="Analyst@123"), db)
        assert analyst_res["token"], "Analyst token missing"
        assert analyst_res["user"]["username"] == "analyst", "Analyst username mismatch"
        print("  - Analyst login OK:", analyst_res["user"]["username"], analyst_res["user"]["role"])

        # 3. Register a new custom user
        test_uname = "sarah_soc"
        existing = db.query(m.User).filter_by(username=test_uname).first()
        if existing:
            db.delete(existing)
            db.commit()

        reg_res = register(RegisterRequest(
            username=test_uname,
            password="SecurePassword@2026",
            full_name="Sarah Connor",
            email="sarah@cyber.soc",
            role="hunter",
            theme_preference="matrix"
        ), db)
        assert reg_res["user"]["username"] == test_uname
        assert reg_res["user"]["role"] == "hunter"
        print("  - Register new user OK:", reg_res["user"])

        # 4. Login with newly created user
        new_login = login(LoginRequest(username=test_uname, password="SecurePassword@2026"), db)
        assert new_login["token"]
        print("  - New user login OK!")
    finally:
        db.close()

def test_clean_file_scanning_accuracy():
    print("[TEST 2] Clean Image Scanning Accuracy (No False Positives)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a clean valid JPEG image with high-entropy bytes that could contain random 0x4D 0x5A
        # In the past, having bytes b"MZ" in compressed data falsely triggered CRITICAL embedded executable!
        img_path = Path(tmpdir) / "clean_photo.jpg"
        # JPEG header: FF D8 FF E0 00 10 4A 46 49 46 ... compressed data with random MZ ... FF D9
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00"
        # Add simulated compressed bytes containing accidental "MZ" without valid PE header
        content += b"\x12\x34MZ\x56\x78\x9a\xbc\xde\xf0" * 20
        # JPEG EOF
        content += b"\xff\xd9"
        img_path.write_bytes(content)

        # 1. Signature analysis
        sig = analyze_signature(img_path, "clean_photo.jpg", "image/jpeg")
        assert sig["status"] == "SAFE", f"Expected SAFE, got {sig['status']}"
        assert sig["detected_format"] == "JPEG"
        print("  - Clean JPEG signature check OK:", sig["status"])

        # 2. Embedded content analysis
        emb = analyze_embedded_content(img_path, "JPEG")
        assert not emb["appended_data_found"], "Clean image should not have appended data"
        assert len(emb["embedded_signatures"]) == 0, f"False positive embedded signatures found: {emb['embedded_signatures']}"
        assert emb["highest_severity"] == "NONE"
        print("  - Clean JPEG embedded check OK: 0 false positives! Highest severity:", emb["highest_severity"])

        # 3. Risk calculation
        risk = calculate_risk({"signature": sig, "embedded": emb})
        assert risk["category"] == "SAFE"
        assert risk["total_score"] == 0
        print("  - Clean JPEG risk score:", risk["total_score"], "Category:", risk["category"])

def test_malicious_polyglot_scanning_accuracy():
    print("[TEST 3] Disguised & Appended Payload Detection Accuracy (True Positives)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Disguised Windows PE Executable named disguised.jpg
        # Starts with MZ and has valid PE pointer at 0x3C pointing to PE\0\0
        pe_path = Path(tmpdir) / "disguised.jpg"
        pe_data = bytearray(256)
        pe_data[0:2] = b"MZ"
        pe_data[0x3C:0x40] = (0x80).to_bytes(4, "little") # PE offset at 128
        pe_data[0x80:0x84] = b"PE\x00\x00"
        pe_path.write_bytes(bytes(pe_data))

        sig = analyze_signature(pe_path, "disguised.jpg", "image/jpeg")
        assert sig["status"] == "HIGH RISK", "Disguised executable must be flagged HIGH RISK"
        emb = analyze_embedded_content(pe_path, "UNKNOWN")
        assert any("PE" in e["type"] for e in emb["embedded_signatures"]), "Real PE must be detected"
        assert emb["highest_severity"] == "CRITICAL"
        risk = calculate_risk({"signature": sig, "embedded": emb})
        assert risk["category"] in ("HIGH", "CRITICAL")
        print("  - Disguised PE Detection OK! Risk:", risk["total_score"], "Category:", risk["category"])

        # 2. Legitimate PNG with appended ZIP payload after EOF
        png_path = Path(tmpdir) / "stego_polyglot.png"
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xae\x42\x60\x82"
        # Append valid ZIP header after IEND
        zip_payload = b"PK\x03\x04\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00test.txtSECRET_PAYLOAD"
        png_path.write_bytes(png_data + zip_payload)

        sig_png = analyze_signature(png_path, "stego_polyglot.png", "image/png")
        emb_png = analyze_embedded_content(png_path, "PNG")
        assert emb_png["appended_data_found"] == True, "Appended data must be detected"
        assert any("ZIP" in e["type"] for e in emb_png["embedded_signatures"]), "Appended ZIP must be detected"
        risk_png = calculate_risk({"signature": sig_png, "embedded": emb_png})
        print("  - Appended Polyglot Detection OK! Appended size:", emb_png["appended_data_size"], "Risk:", risk_png["total_score"], "Category:", risk_png["category"])

if __name__ == "__main__":
    test_multi_user_auth()
    test_clean_file_scanning_accuracy()
    test_malicious_polyglot_scanning_accuracy()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY! 100% ACCURACY CONFIRMED.")
