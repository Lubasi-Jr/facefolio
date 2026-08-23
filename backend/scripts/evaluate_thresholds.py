"""Offline threshold calibration for face-match confidence bands.

Computes cosine-similarity distributions for labeled genuine (same person) and
impostor (different person) face pairs, using the exact same InsightFace model
as production (app/cv), and suggests T_high / T_low starting points from the
measured distributions.

This does NOT read or write settings.py, and it must not be trusted blindly —
it is the input to a human decision, not an automatic calibrator. Re-run it
whenever the reference dataset changes meaningfully.

Expected input layout (each pair dir holds exactly two images of one pair):

    <genuine-dir>/
      pair_001/
        a.jpg
        b.jpg
      pair_002/
        ...
    <impostor-dir>/
      pair_001/
        a.jpg
        b.jpg
      ...

Each image must contain exactly one detectable face; pairs that don't satisfy
that (or don't have exactly two images) are skipped and logged, not counted.

Run inside the backend container so the model matches production exactly:

    docker compose run --rm \\
      -v /path/to/eval_pairs:/data/eval_pairs \\
      -v /path/to/report_out:/data/report_out \\
      backend \\
      uv run python scripts/evaluate_thresholds.py \\
        --genuine-dir /data/eval_pairs/genuine \\
        --impostor-dir /data/eval_pairs/impostor \\
        --out-dir /data/report_out \\
        --csv
"""

import argparse
import csv
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import structlog

from app.cv.detector import detect_faces
from app.cv.embedder import normalize_face_embedding
from app.cv.imaging import load_bgr
from app.logging_config import configure_logging

log = structlog.get_logger()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass
class PairResult:
    pair_dir: str
    similarity: float


def _find_pair_images(pair_dir: Path) -> list[Path]:
    return sorted(p for p in pair_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)


def _embed_single_face(image_path: Path) -> np.ndarray | None:
    """Detects+embeds the one face expected in image_path, or None if the
    image doesn't have exactly one detectable face. Reuses app/cv end to end
    (detector for detection/embedding, embedder for L2 normalization) so this
    script can never drift from how production embeds faces.
    """
    image = load_bgr(image_path)
    detections = detect_faces(image)

    if len(detections) != 1:
        log.warning(
            "evaluate_thresholds.embed_skipped",
            image=str(image_path),
            face_count=len(detections),
        )
        return None

    return normalize_face_embedding(detections[0].embedding)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Both vectors are L2-normalized (app/cv/embedder.py), so cosine similarity
    # reduces to a plain dot product — matches `1 - (embedding <=> :vec)` in
    # the pgvector query this is calibrating a threshold for.
    return float(np.dot(a, b))


def compute_pair_similarities(pairs_dir: Path, label: str) -> list[PairResult]:
    pair_dirs = sorted(p for p in pairs_dir.iterdir() if p.is_dir())
    if not pair_dirs:
        log.warning("evaluate_thresholds.no_pairs_found", dir=str(pairs_dir), label=label)

    results: list[PairResult] = []
    for pair_dir in pair_dirs:
        images = _find_pair_images(pair_dir)
        if len(images) != 2:
            log.warning(
                "evaluate_thresholds.pair_skipped",
                pair_dir=str(pair_dir),
                label=label,
                reason="expected_2_images",
                found=len(images),
            )
            continue

        embedding_a = _embed_single_face(images[0])
        embedding_b = _embed_single_face(images[1])
        if embedding_a is None or embedding_b is None:
            log.warning(
                "evaluate_thresholds.pair_skipped",
                pair_dir=str(pair_dir),
                label=label,
                reason="embedding_failed",
            )
            continue

        similarity = _cosine_similarity(embedding_a, embedding_b)
        results.append(PairResult(pair_dir=pair_dir.name, similarity=similarity))
        log.info(
            "evaluate_thresholds.pair_scored",
            pair_dir=pair_dir.name,
            label=label,
            similarity=round(similarity, 4),
        )

    return results


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def _percentile(values: list[float], pct: float) -> float:
    return float(np.percentile(values, pct))


def suggest_thresholds(genuine: list[float], impostor: list[float]) -> tuple[float, float]:
    """Suggests T_high / T_low from measured distributions.

    T_high: the 99th percentile of impostor similarities, so auto-tagging
    above T_high should misfire on roughly 1 in 100 impostor pairs.
    T_low: the 5th percentile of genuine similarities, so the "needs guest
    confirmation" band (t_low..t_high) still catches roughly 95% of true
    matches instead of silently dropping them.

    These are starting points for a human to sanity-check against the printed
    recall/false-accept numbers, not a final answer — see module docstring.
    """
    t_high = _percentile(impostor, 99)
    t_low = _percentile(genuine, 5)
    return t_high, t_low


def _recall_at(genuine: list[float], threshold: float) -> float:
    return sum(1 for s in genuine if s >= threshold) / len(genuine)


def _false_accept_rate_at(impostor: list[float], threshold: float) -> float:
    return sum(1 for s in impostor if s >= threshold) / len(impostor)


def _format_stats_table(genuine_stats: dict, impostor_stats: dict) -> str:
    rows = ["| | genuine | impostor |", "|---|---|---|"]
    for key in ("n", "min", "max", "mean", "median", "std"):
        g, i = genuine_stats[key], impostor_stats[key]
        if key == "n":
            rows.append(f"| n | {g} | {i} |")
        else:
            rows.append(f"| {key} | {g:.4f} | {i:.4f} |")
    return "\n".join(rows)


def build_report(
    genuine: list[float],
    impostor: list[float],
    genuine_stats: dict,
    impostor_stats: dict,
    t_high: float,
    t_low: float,
) -> str:
    recall_at_high = _recall_at(genuine, t_high)
    far_at_high = _false_accept_rate_at(impostor, t_high)
    recall_at_low = _recall_at(genuine, t_low)
    far_at_low = _false_accept_rate_at(impostor, t_low)

    warning = ""
    if t_low >= t_high:
        warning = (
            "\n**Warning:** suggested T_low >= T_high — the genuine and impostor "
            "distributions overlap too much for a clean band with this dataset. "
            "Collect more/better pairs before trusting these numbers.\n"
        )

    generated_at = datetime.now(timezone.utc).isoformat()

    return f"""# Threshold calibration report

Generated: {generated_at}

Do not assume these numbers — this report is the input to a human decision,
not a substitute for one. Re-run against a larger/representative dataset
before changing production thresholds.

## Distribution stats (cosine similarity)

{_format_stats_table(genuine_stats, impostor_stats)}
{warning}
## Suggested thresholds

- **T_high = {t_high:.4f}** (impostor 99th percentile) — auto-tag recall {recall_at_high:.1%} of genuine pairs, false-accepts {far_at_high:.1%} of impostor pairs at this cutoff.
- **T_low = {t_low:.4f}** (genuine 5th percentile) — confirmation-band recall {recall_at_low:.1%} of genuine pairs, false-accepts {far_at_low:.1%} of impostor pairs at this cutoff.

match_margin is not suggested here — it depends on the runner-up-similarity
gap for ambiguous photos (e.g. near-duplicate faces in a crowd shot), which
this pairwise genuine/impostor dataset doesn't measure. Tune it separately
against real event galleries.

## Counts

- Genuine pairs scored: {genuine_stats["n"]}
- Impostor pairs scored: {impostor_stats["n"]}
"""


def _write_csv(path: Path, genuine: list[PairResult], impostor: list[PairResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "pair_dir", "similarity"])
        for r in genuine:
            writer.writerow(["genuine", r.pair_dir, f"{r.similarity:.6f}"])
        for r in impostor:
            writer.writerow(["impostor", r.pair_dir, f"{r.similarity:.6f}"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--genuine-dir", type=Path, required=True, help="Dir of genuine (same-person) pair subdirs.")
    parser.add_argument("--impostor-dir", type=Path, required=True, help="Dir of impostor (different-person) pair subdirs.")
    parser.add_argument("--out-dir", type=Path, default=Path("threshold_report"), help="Where to write the report (and CSV).")
    parser.add_argument("--csv", action="store_true", help="Also write raw per-pair similarities as CSV, for plotting.")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    log.info(
        "evaluate_thresholds.started",
        genuine_dir=str(args.genuine_dir),
        impostor_dir=str(args.impostor_dir),
        out_dir=str(args.out_dir),
    )

    genuine_results = compute_pair_similarities(args.genuine_dir, "genuine")
    impostor_results = compute_pair_similarities(args.impostor_dir, "impostor")

    if len(genuine_results) < 2 or len(impostor_results) < 2:
        log.error(
            "evaluate_thresholds.insufficient_data",
            genuine_scored=len(genuine_results),
            impostor_scored=len(impostor_results),
        )
        print(
            "Not enough scored pairs to compute statistics "
            f"(genuine={len(genuine_results)}, impostor={len(impostor_results)}). "
            "Need at least 2 of each — check the warnings above for skipped pairs.",
            file=sys.stderr,
        )
        sys.exit(1)

    genuine_sims = [r.similarity for r in genuine_results]
    impostor_sims = [r.similarity for r in impostor_results]

    genuine_stats = _stats(genuine_sims)
    impostor_stats = _stats(impostor_sims)
    t_high, t_low = suggest_thresholds(genuine_sims, impostor_sims)

    report = build_report(genuine_sims, impostor_sims, genuine_stats, impostor_stats, t_high, t_low)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "threshold_report.md"
    report_path.write_text(report, encoding="utf-8")

    csv_path = None
    if args.csv:
        csv_path = args.out_dir / "similarities.csv"
        _write_csv(csv_path, genuine_results, impostor_results)

    log.info(
        "evaluate_thresholds.completed",
        genuine_scored=genuine_stats["n"],
        impostor_scored=impostor_stats["n"],
        suggested_t_high=round(t_high, 4),
        suggested_t_low=round(t_low, 4),
        report_path=str(report_path),
        csv_path=str(csv_path) if csv_path else None,
    )

    print(report)
    print(f"Report written to {report_path}")
    if csv_path:
        print(f"Raw similarities written to {csv_path}")


if __name__ == "__main__":
    main()
