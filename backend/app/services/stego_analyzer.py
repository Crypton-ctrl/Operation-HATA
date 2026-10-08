"""
Steganography Analysis
Heuristic indicators of hidden data: LSB (least-significant-bit) statistical
anomalies and a chi-square test on pixel value pair distributions - a classic,
well-documented approach for detecting naive LSB steganography.

This module NEVER claims mathematical certainty. Results are classified into
NOT DETECTED / POSSIBLE / SUSPICIOUS / HIGHLY SUSPICIOUS bands.
"""
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


def _lsb_randomness_score(channel: "np.ndarray") -> float:
    """Ratio of set LSBs. True random/hidden data pushes this close to 0.5.
    Natural images tend to deviate somewhat from exactly 0.5."""
    lsb = channel & 1
    return float(lsb.mean())


def _chi_square_pairs(channel: "np.ndarray") -> float:
    """Chi-square statistic on even/odd value pair frequencies - a standard
    LSB-steganography detection heuristic. Higher values suggest pixel value
    pairs have been artificially equalized (a hallmark of naive LSB embedding)."""
    flat = channel.flatten()
    hist = np.bincount(flat, minlength=256).astype(float)
    chi = 0.0
    pairs = 0
    for i in range(0, 256, 2):
        obs_even, obs_odd = hist[i], hist[i + 1]
        expected = (obs_even + obs_odd) / 2.0
        if expected > 0:
            chi += ((obs_even - expected) ** 2) / expected
            chi += ((obs_odd - expected) ** 2) / expected
            pairs += 1
    return float(chi / max(pairs, 1))


def analyze_steganography(file_path: Path) -> dict:
    if not PIL_AVAILABLE:
        return {
            "classification": "NOT DETECTED",
            "lsb_score": None,
            "chi_square_score": None,
            "indicators": [],
            "notes": "Steganography module unavailable (Pillow/numpy not installed). "
                     "This result reflects tool unavailability, not a confirmed absence of hidden data.",
        }

    indicators = []
    try:
        with Image.open(file_path) as img:
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGB")
            arr = np.array(img)

        if arr.ndim == 2:
            channels = {"gray": arr}
        else:
            names = ["red", "green", "blue", "alpha"][: arr.shape[2]]
            channels = {names[i]: arr[:, :, i] for i in range(arr.shape[2])}

        lsb_scores = {}
        chi_scores = {}
        for name, ch in channels.items():
            lsb_scores[name] = _lsb_randomness_score(ch)
            chi_scores[name] = _chi_square_pairs(ch)

        avg_lsb = sum(lsb_scores.values()) / len(lsb_scores)
        avg_chi = sum(chi_scores.values()) / len(chi_scores)

        # LSB ratio very close to 0.5 across all channels is a mild indicator.
        lsb_deviation = abs(avg_lsb - 0.5)
        if lsb_deviation < 0.003:
            indicators.append({
                "type": "LSB near-perfect randomness",
                "detail": f"Average LSB set-ratio {avg_lsb:.4f} is unusually close to 0.5 across channels.",
            })

        # Low chi-square (near-equalized even/odd pairs) is a classic naive-LSB signal.
        if avg_chi < 8:
            indicators.append({
                "type": "Chi-square pair equalization",
                "detail": f"Average chi-square statistic {avg_chi:.2f} suggests possible equalized "
                          f"pixel-value pairs, a pattern associated with naive LSB embedding.",
            })

        score = 0
        if lsb_deviation < 0.003:
            score += 1
        if avg_chi < 4:
            score += 2
        elif avg_chi < 8:
            score += 1

        if score >= 3:
            classification = "HIGHLY SUSPICIOUS"
        elif score == 2:
            classification = "SUSPICIOUS"
        elif score == 1:
            classification = "POSSIBLE"
        else:
            classification = "NOT DETECTED"

        notes = (
            "Statistical indicators only - these heuristics can produce false positives on "
            "noisy or heavily-compressed images and false negatives on sophisticated steganography. "
            "Treat as supporting evidence, not proof."
        )

        return {
            "classification": classification,
            "lsb_score": round(avg_lsb, 4),
            "chi_square_score": round(avg_chi, 2),
            "indicators": indicators,
            "notes": notes,
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "classification": "NOT DETECTED",
            "lsb_score": None,
            "chi_square_score": None,
            "indicators": [],
            "notes": f"Steganography analysis failed to run: {exc}",
        }
