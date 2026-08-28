"""Thin wrapper around fastembed so index-build and runtime embed identically."""
from __future__ import annotations

import numpy as np
from fastembed import TextEmbedding

from app.config import Settings


class Embedder:
    def __init__(self, settings: Settings):
        self.model = TextEmbedding(
            model_name=settings.embedding_model,
            cache_dir=settings.embedding_cache_dir,
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return an (N, dim) float32 matrix of L2-normalized embeddings."""
        vecs = np.array(list(self.model.embed(texts)), dtype="float32")
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / np.clip(norms, 1e-12, None)
