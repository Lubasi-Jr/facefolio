"""L2 normalization of face embeddings.

Detection (app/cv/detector.py) deliberately returns InsightFace's raw,
un-normalized embedding — normalizing is a separate, explicit step owned
here, done right before an embedding is written to the database. Storing
normalized vectors lets cosine similarity be computed downstream as
`1 - (embedding <=> :vec)` (pgvector's cosine-distance operator) without
needing to renormalize at query time.
"""

import numpy as np
import structlog

log = structlog.get_logger()

EMBEDDING_DIM = 512


def normalize(embedding: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(embedding)
    if norm == 0:
        raise ValueError("cannot normalize a zero vector")
    return embedding / norm


def normalize_face_embedding(raw_embedding: np.ndarray) -> np.ndarray:
    if raw_embedding.shape != (EMBEDDING_DIM,):
        raise ValueError(
            f"expected a {EMBEDDING_DIM}-d embedding, got shape {raw_embedding.shape}"
        )

    normalized = normalize(raw_embedding.astype(np.float32))

    # Never log the vector itself (biometric data) — shape/norm only.
    log.debug(
        "cv.embedder.normalized",
        dims=normalized.shape[0],
        norm=float(np.linalg.norm(normalized)),
    )

    return normalized
