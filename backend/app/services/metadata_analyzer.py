"""
Image Metadata / EXIF Analysis
Uses Pillow (and piexif where available) to extract EXIF data.
Metadata only contributes to risk when genuinely suspicious - normal
camera/software metadata is never automatically flagged as malicious.
"""
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

SUSPICIOUS_SOFTWARE_KEYWORDS = [
    "photoshop script", "exiftool", "steghide", "openstego", "outguess",
    "hex editor", "010 editor",
]


def _decode_gps(gps_info: dict) -> dict | None:
    if not gps_info:
        return None
    try:
        def to_deg(value):
            d, m, s = value
            return float(d) + float(m) / 60 + float(s) / 3600

        lat = to_deg(gps_info.get(2, (0, 0, 0)))
        if gps_info.get(1) == "S":
            lat = -lat
        lon = to_deg(gps_info.get(4, (0, 0, 0)))
        if gps_info.get(3) == "W":
            lon = -lon
        return {"latitude": round(lat, 6), "longitude": round(lon, 6)}
    except Exception:
        return {"raw": True}


def analyze_metadata(file_path: Path) -> dict:
    result = {
        "camera_make": None, "camera_model": None, "software": None,
        "created_date": None, "modified_date": None,
        "gps_present": False, "gps_data": None,
        "width": None, "height": None, "color_profile": None,
        "raw_exif": {}, "anomalies": [], "anomaly_detected": False,
    }

    if not PIL_AVAILABLE:
        result["anomalies"].append({
            "finding": "Metadata module unavailable (Pillow not installed)",
            "severity": "info",
        })
        return result

    try:
        with Image.open(file_path) as img:
            result["width"], result["height"] = img.size
            result["color_profile"] = img.mode

            exif_raw = {}
            gps_info = {}
            try:
                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag == "GPSInfo":
                            for gk, gv in value.items():
                                gps_tag = ExifTags.GPSTAGS.get(gk, gk)
                                gps_info[gk] = gv
                                exif_raw[f"GPS.{gps_tag}"] = str(gv)
                        else:
                            if isinstance(value, bytes):
                                value = value.decode(errors="replace")
                            exif_raw[tag] = str(value)[:200]
            except Exception:
                pass

            result["raw_exif"] = exif_raw
            result["camera_make"] = exif_raw.get("Make")
            result["camera_model"] = exif_raw.get("Model")
            result["software"] = exif_raw.get("Software")
            result["created_date"] = exif_raw.get("DateTimeOriginal") or exif_raw.get("DateTime")
            result["modified_date"] = exif_raw.get("DateTime")

            if gps_info:
                result["gps_present"] = True
                result["gps_data"] = _decode_gps(gps_info)

            # --- Anomaly heuristics (only flag genuinely suspicious patterns) ---
            anomalies = []

            if result["software"]:
                sw_lower = result["software"].lower()
                if any(k in sw_lower for k in SUSPICIOUS_SOFTWARE_KEYWORDS):
                    anomalies.append({
                        "finding": f"Software field references a known steganography/editing tool: '{result['software']}'",
                        "severity": "medium",
                    })

            if len(exif_raw) > 60:
                anomalies.append({
                    "finding": f"Unusually large number of metadata fields present ({len(exif_raw)}).",
                    "severity": "low",
                })

            created = result["created_date"]
            modified = result["modified_date"]
            if created and modified and created != modified:
                try:
                    fmt = "%Y:%m:%d %H:%M:%S"
                    c_dt = datetime.strptime(created, fmt)
                    m_dt = datetime.strptime(modified, fmt)
                    if m_dt < c_dt:
                        anomalies.append({
                            "finding": "Modification timestamp is earlier than creation timestamp (conflicting timestamps).",
                            "severity": "low",
                        })
                except Exception:
                    pass

            # Unusually long/binary-looking custom fields can indicate data hidden in metadata
            for k, v in exif_raw.items():
                if k.startswith("GPS"):
                    continue
                if isinstance(v, str) and len(v) > 500:
                    anomalies.append({
                        "finding": f"EXIF field '{k}' contains an unusually large value ({len(v)} chars) - possible data hidden in metadata.",
                        "severity": "medium",
                    })

            result["anomalies"] = anomalies
            result["anomaly_detected"] = len(anomalies) > 0

    except Exception as exc:  # noqa: BLE001
        result["anomalies"].append({
            "finding": f"Metadata extraction failed: {exc}",
            "severity": "info",
        })

    return result
