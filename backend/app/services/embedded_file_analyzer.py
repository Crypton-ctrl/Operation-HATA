"""
Appended Data & Embedded File Detection
Accurately checks for data after the expected end-of-file marker of common image formats,
and scans the file for structurally verified signatures of ZIPs, PDFs, executables, and
scripts concatenated onto or embedded within the image. Extracted content is NEVER executed.
"""
from pathlib import Path

# Known EOF markers for supported formats
EOF_MARKERS = {
    "JPEG": b"\xff\xd9",
    "PNG": b"IEND\xae\x42\x60\x82",
    "GIF": b"\x3b",
}

SEVERITY_ORDER = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _find_expected_eof(file_bytes: bytes, fmt: str | None) -> int | None:
    if not fmt:
        return None
    marker = EOF_MARKERS.get(fmt)
    if not marker:
        return None
    idx = file_bytes.rfind(marker)
    if idx == -1:
        return None
    return idx + len(marker)


def _verify_pe_executable(data: bytes, offset: int) -> bool:
    """Verifies that an MZ signature at offset is genuinely a Windows PE executable."""
    # Need at least 0x40 bytes for DOS header
    if offset + 0x40 > len(data):
        return False
    # Check e_lfanew pointer at offset 0x3C
    pe_ptr = int.from_bytes(data[offset + 0x3C : offset + 0x40], "little")
    if pe_ptr < 0x40 or pe_ptr > 0x1000:
        return False
    pe_offset = offset + pe_ptr
    if pe_offset + 4 > len(data):
        return False
    # Must have "PE\x00\x00" signature at e_lfanew
    return data[pe_offset : pe_offset + 4] == b"PE\x00\x00"


def _verify_elf_executable(data: bytes, offset: int) -> bool:
    """Verifies that an ELF signature at offset is a genuine ELF binary."""
    if offset + 16 > len(data):
        return False
    ei_class = data[offset + 4]  # 1 = 32-bit, 2 = 64-bit
    ei_data = data[offset + 5]   # 1 = little-endian, 2 = big-endian
    ei_version = data[offset + 6]  # 1 = current
    return ei_class in (1, 2) and ei_data in (1, 2) and ei_version == 1


def _verify_zip_archive(data: bytes, offset: int) -> bool:
    """Verifies that PK\x03\x04 is a genuine ZIP local file header."""
    if offset + 30 > len(data):
        return False
    # Version needed to extract (usually 10, 20, 45, etc.)
    version = int.from_bytes(data[offset + 4 : offset + 6], "little")
    if version > 100:
        return False
    fname_len = int.from_bytes(data[offset + 26 : offset + 28], "little")
    extra_len = int.from_bytes(data[offset + 28 : offset + 30], "little")
    if fname_len > 1024 or extra_len > 4096:
        return False
    return True


def _verify_script_payload(data: bytes, offset: int, sig: bytes) -> bool:
    """Checks if script tag/shebang appears as readable ASCII/script, not random binary noise."""
    end = min(len(data), offset + len(sig) + 40)
    sample = data[offset:end]
    # At least 70% of the sample characters must be printable ASCII
    printable = sum(1 for b in sample if 32 <= b <= 126 or b in (9, 10, 13))
    return (printable / max(len(sample), 1)) >= 0.70


def analyze_embedded_content(file_path: Path, detected_format: str | None) -> dict:
    data = file_path.read_bytes()
    total_size = len(data)

    appended_found = False
    appended_offset = None
    appended_size = None

    eof_pos = _find_expected_eof(data, detected_format)
    if eof_pos is not None and eof_pos < total_size:
        trailing = data[eof_pos:]
        # Ignore trivial trailing null padding, common and benign in some camera outputs
        if len(trailing.strip(b"\x00\r\n ")) > 8:
            appended_found = True
            appended_offset = eof_pos
            appended_size = total_size - eof_pos

    embedded_signatures = []
    highest = "NONE"

    def record_match(item_type: str, offset: int, severity: str, is_appended: bool = False):
        nonlocal highest
        embedded_signatures.append({
            "type": f"Appended {item_type}" if is_appended else item_type,
            "offset": offset,
            "size": total_size - offset,
            "severity": severity,
            "appended": is_appended,
        })
        if SEVERITY_ORDER.index(severity) > SEVERITY_ORDER.index(highest):
            highest = severity

    # 1. Structural search for Windows PE (MZ + PE header)
    search_idx = 0
    while True:
        mz_idx = data.find(b"MZ", search_idx)
        if mz_idx == -1 or mz_idx + 0x40 > total_size:
            break
        if _verify_pe_executable(data, mz_idx):
            is_app = (eof_pos is not None and mz_idx >= eof_pos)
            record_match("Windows PE executable (MZ/PE)", mz_idx, "CRITICAL", is_app)
            break
        search_idx = mz_idx + 2

    # 2. Structural search for ELF executable
    search_idx = 0
    while True:
        elf_idx = data.find(b"\x7fELF", search_idx)
        if elf_idx == -1 or elf_idx + 16 > total_size:
            break
        if _verify_elf_executable(data, elf_idx):
            is_app = (eof_pos is not None and elf_idx >= eof_pos)
            record_match("ELF executable", elf_idx, "CRITICAL", is_app)
            break
        search_idx = elf_idx + 4

    # 3. Structural search for ZIP Archive
    search_idx = 0
    while True:
        zip_idx = data.find(b"PK\x03\x04", search_idx)
        if zip_idx == -1 or zip_idx + 8 > total_size:
            break
        is_app = (eof_pos is not None and zip_idx >= eof_pos)
        # If found in appended data beyond EOF, it is unambiguously an appended archive payload.
        # If found inside the image body, structurally verify header to prevent false positives.
        if is_app or (zip_idx >= 4 and _verify_zip_archive(data, zip_idx)):
            record_match("ZIP archive", zip_idx, "MEDIUM", is_app)
            break
        search_idx = zip_idx + 4

    # 4. Search for RAR archive
    rar_idx = data.find(b"Rar!\x1a\x07", 4)
    if rar_idx != -1:
        is_app = (eof_pos is not None and rar_idx >= eof_pos)
        record_match("RAR archive", rar_idx, "MEDIUM", is_app)

    # 5. Search for 7-Zip archive
    sz_idx = data.find(b"7z\xbc\xaf\x27\x1c", 4)
    if sz_idx != -1:
        is_app = (eof_pos is not None and sz_idx >= eof_pos)
        record_match("7-Zip archive", sz_idx, "MEDIUM", is_app)

    # 6. Search for PDF document
    pdf_idx = data.find(b"%PDF-", 4)
    if pdf_idx != -1:
        is_app = (eof_pos is not None and pdf_idx >= eof_pos)
        record_match("PDF document", pdf_idx, "LOW", is_app)

    # 7. Script payloads (verified in appended data or uncompressed strings)
    scripts = [
        (b"#!/bin/", "Shell script shebang", "HIGH"),
        (b"<?php", "PHP script tag", "HIGH"),
        (b"<script", "HTML/script tag", "MEDIUM"),
        (b"eval(base64_decode", "Obfuscated script loader", "HIGH"),
    ]
    for sig, desc, sev in scripts:
        idx = data.find(sig, 4)
        if idx != -1:
            is_app = (eof_pos is not None and idx >= eof_pos)
            # Only count if in appended area or verified readable script
            if is_app or _verify_script_payload(data, idx, sig):
                record_match(desc, idx, sev, is_app)

    return {
        "appended_data_found": appended_found,
        "appended_data_offset": appended_offset,
        "appended_data_size": appended_size,
        "embedded_signatures": embedded_signatures,
        "highest_severity": highest,
    }
