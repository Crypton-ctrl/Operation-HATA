"""
YARA Scanning Service
Compiles all .yar rules found under rules/yara/**/ and scans the quarantined
file. If yara-python is not installed, the scan continues and reports that
the YARA engine is unavailable rather than failing the whole pipeline.
"""
from pathlib import Path
from app.config import get_settings

settings = get_settings()

try:
    import yara
    YARA_AVAILABLE = True
except Exception:
    YARA_AVAILABLE = False

_compiled_rules = None
_rule_count = 0


def _compile_rules():
    global _compiled_rules, _rule_count
    if not YARA_AVAILABLE:
        return None
    rule_files = list(settings.YARA_RULES_DIR.rglob("*.yar"))
    if not rule_files:
        return None
    filepaths = {f"ns{i}": str(f) for i, f in enumerate(rule_files)}
    try:
        _compiled_rules = yara.compile(filepaths=filepaths)
        _rule_count = len(rule_files)
        return _compiled_rules
    except Exception:
        return None


def scan_with_yara(file_path: Path) -> dict:
    if not YARA_AVAILABLE:
        return {
            "rules_scanned": 0,
            "matches": [],
            "engine_available": False,
        }

    global _compiled_rules
    if _compiled_rules is None:
        _compile_rules()

    if _compiled_rules is None:
        return {"rules_scanned": 0, "matches": [], "engine_available": False}

    try:
        matches = _compiled_rules.match(str(file_path))
        results = []
        for m in matches:
            results.append({
                "rule": m.rule,
                "description": m.meta.get("description", ""),
                "severity": m.meta.get("severity", "LOW"),
            })
        return {
            "rules_scanned": _rule_count,
            "matches": results,
            "engine_available": True,
        }
    except Exception:
        return {"rules_scanned": _rule_count, "matches": [], "engine_available": False}
