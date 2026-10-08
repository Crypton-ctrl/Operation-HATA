"""
Entropy Analysis
Calculates Shannon entropy of the file overall and in chunks (for visualization).
High entropy alone never proves malware - it is one signal among several,
since compressed image formats naturally have moderately high entropy.
"""
import math
from collections import Counter
from pathlib import Path


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 4)


def analyze_entropy(file_path: Path, chunk_count: int = 20) -> dict:
    data = file_path.read_bytes()
    overall = shannon_entropy(data)

    n = len(data)
    header = data[: min(4096, n)]
    tail = data[-min(4096, n):] if n > 0 else b""
    body = data[4096: max(4096, n - 4096)] if n > 8192 else data

    chunk_entropies = []
    if n > 0:
        step = max(1, n // chunk_count)
        for i in range(0, n, step):
            chunk = data[i:i + step]
            chunk_entropies.append({
                "offset": i,
                "entropy": shannon_entropy(chunk),
            })

    # Classification: JPEG/PNG compressed data is typically ~7.5-8.0 bits/byte.
    # We flag only significantly elevated, uniformly-high entropy across the *tail*
    # region beyond what's typical, since that often indicates encrypted/packed
    # appended data rather than normal image compression.
    classification = "NORMAL"
    anomaly = False
    if overall >= 7.95 and shannon_entropy(tail) >= 7.9 and n > 20000:
        classification = "HIGH"
        anomaly = True
    elif overall >= 7.8:
        classification = "ELEVATED"

    return {
        "overall_entropy": overall,
        "header_entropy": shannon_entropy(header),
        "body_entropy": shannon_entropy(body),
        "tail_entropy": shannon_entropy(tail),
        "chunk_entropies": chunk_entropies,
        "classification": classification,
        "anomaly_detected": anomaly,
    }
