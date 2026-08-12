"""Learned and neural matchers.

Three tiers, with very different availability:

``CharEmbeddingMatcher``
    Character n-gram TF-IDF reduced by truncated SVD, fitted on the corpus's
    own name vocabulary. Runs anywhere scikit-learn is installed, needs no
    downloads, and is a genuinely learned low-dimensional representation rather
    than raw n-gram overlap.

``SentenceEncoderMatcher``
    MuRIL or LaBSE cosine similarity. Requires ``transformers`` and a model
    download. This is the only family that can score above zero on the
    cross-script split, because it is the only one with a shared representation
    across scripts.

``LLMRerankerMatcher``
    An LLM adjudicating candidates from a cheap first stage. Requires an API
    key and costs real money per pair, so it is only sensible as the final
    stage of a cascade.

Availability is reported explicitly. A matcher that could not run must never
appear in a results table as one that scored badly.
"""

from __future__ import annotations

import os
from typing import ClassVar

from .base import CostClass, Matcher, clamp, normalise

try:  # pragma: no cover
    import numpy as np
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    _HAVE_SKLEARN = True
except ImportError:  # pragma: no cover
    _HAVE_SKLEARN = False

try:  # pragma: no cover
    import sentence_transformers  # noqa: F401

    _HAVE_SENTENCE_TRANSFORMERS = True
except ImportError:  # pragma: no cover
    _HAVE_SENTENCE_TRANSFORMERS = False

try:  # pragma: no cover
    import anthropic  # noqa: F401

    _HAVE_ANTHROPIC = True
except ImportError:  # pragma: no cover
    _HAVE_ANTHROPIC = False


class CharEmbeddingMatcher(Matcher):
    """Character n-gram TF-IDF projected to a dense space by truncated SVD.

    Must be fitted before use. Fitting on the benchmark's own vocabulary is
    legitimate here because the representation is unsupervised -- it sees name
    strings, never pair labels -- but it does mean the matcher has seen the
    corpus's orthographic distribution, which a deployed system would not have.
    Treat its numbers as a mild upper bound and read the caveat in
    reports/findings.md.
    """

    name: ClassVar[str] = "char_embedding_svd"
    cost_class: ClassVar[CostClass] = CostClass.CHEAP
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Character n-gram TF-IDF + truncated SVD cosine"

    def __init__(self, dimensions: int = 128, ngram_range: tuple[int, int] = (2, 4)):
        self.dimensions = dimensions
        self.ngram_range = ngram_range
        self._vectoriser = None
        self._svd = None
        self._cache: dict[str, object] = {}

    @property
    def fitted(self) -> bool:
        return self._svd is not None

    def fit(self, corpus: list[str]) -> CharEmbeddingMatcher:
        if not _HAVE_SKLEARN:  # pragma: no cover
            raise RuntimeError("char_embedding_svd requires the 'report' extra (scikit-learn)")
        texts = sorted({normalise(t) for t in corpus if t.strip()})
        self._vectoriser = TfidfVectorizer(
            analyzer="char_wb", ngram_range=self.ngram_range, min_df=1
        )
        matrix = self._vectoriser.fit_transform(texts)
        components = min(self.dimensions, min(matrix.shape) - 1)
        # random_state fixed: an unseeded SVD would make every reported number
        # irreproducible from the committed config.
        self._svd = TruncatedSVD(n_components=max(2, components), random_state=20260811)
        self._svd.fit(matrix)
        self._cache.clear()
        return self

    def _embed(self, text: str):
        key = normalise(text)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        vector = self._svd.transform(self._vectoriser.transform([key]))[0]
        norm = float(np.linalg.norm(vector))
        unit = vector / norm if norm > 0 else vector
        self._cache[key] = unit
        return unit

    def score(self, a: str, b: str) -> float:
        if not self.fitted:
            raise RuntimeError("CharEmbeddingMatcher.fit() must be called before scoring")
        left, right = self._embed(a), self._embed(b)
        # Cosine lives in [-1, 1]; rescale so the interface contract holds.
        return clamp((float(np.dot(left, right)) + 1.0) / 2.0)

    def score_batch(self, pairs):
        """Embed every distinct string in one transform, then take dot products.

        Per-string ``transform`` calls dominate the runtime otherwise -- around
        1.7ms per pair, which is sklearn call overhead rather than anything
        intrinsic, and reporting it as this method's cost would misrepresent
        its deployability by three orders of magnitude.
        """
        import time

        if not self.fitted:
            raise RuntimeError("CharEmbeddingMatcher.fit() must be called before scoring")

        start = time.perf_counter()
        unique = sorted({normalise(s) for pair in pairs for s in pair})
        matrix = self._svd.transform(self._vectoriser.transform(unique))
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms > 0)
        index = {text: i for i, text in enumerate(unique)}

        scores = [
            clamp((float(matrix[index[normalise(a)]] @ matrix[index[normalise(b)]]) + 1.0) / 2.0)
            for a, b in pairs
        ]
        from .base import Timing

        return scores, Timing(len(pairs), time.perf_counter() - start)


class SentenceEncoderMatcher(Matcher):  # pragma: no cover - needs a model download
    """Multilingual sentence-encoder cosine similarity (MuRIL, LaBSE)."""

    cost_class: ClassVar[CostClass] = CostClass.EXPENSIVE
    handles_non_latin: ClassVar[bool] = True

    def __init__(self, model_id: str = "sentence-transformers/LaBSE", name: str | None = None):
        self.model_id = model_id
        self.name = name or f"encoder[{model_id.split('/')[-1]}]"
        self.description = f"Sentence-encoder cosine ({model_id})"
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_id)
        return self._model

    def score(self, a: str, b: str) -> float:
        model = self._load()
        vectors = model.encode([a, b], normalize_embeddings=True)
        return clamp((float(vectors[0] @ vectors[1]) + 1.0) / 2.0)


class LLMRerankerMatcher(Matcher):  # pragma: no cover - needs an API key
    """LLM adjudication of a candidate pair.

    Intended as the final stage of a cascade, never as a first-pass scorer:
    at screening volume a per-pair model call is several orders of magnitude
    too expensive. The cost-per-pair column in the results is the point of
    including it.
    """

    name: ClassVar[str] = "llm_reranker"
    cost_class: ClassVar[CostClass] = CostClass.VERY_EXPENSIVE
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "LLM adjudication of candidate pairs"

    PROMPT: ClassVar[str] = (
        "You are assisting with sanctions screening on South Asian names. "
        "Two name records are given. Answer with a single probability between "
        "0 and 1 that they refer to the SAME person, accounting for "
        "transliteration variation, honorifics, initials, name-order "
        "differences and community suffixes. Respond with the number only.\n\n"
        "A: {a}\nB: {b}"
    )

    def __init__(self, model: str = "claude-opus-5"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def score(self, a: str, b: str) -> float:
        response = self._get_client().messages.create(
            model=self.model,
            max_tokens=8,
            messages=[{"role": "user", "content": self.PROMPT.format(a=a, b=b)}],
        )
        try:
            return clamp(float(response.content[0].text.strip()))
        except (ValueError, IndexError, AttributeError):
            return 0.0


def build() -> list[Matcher]:
    """Neural matchers constructible in this environment.

    ``CharEmbeddingMatcher`` is returned unfitted; the harness fits it on the
    corpus vocabulary before scoring.
    """
    matchers: list[Matcher] = []
    if _HAVE_SKLEARN:
        matchers.append(CharEmbeddingMatcher())
    if _HAVE_SENTENCE_TRANSFORMERS and os.environ.get("INDIC_BENCH_ENABLE_ENCODERS"):
        matchers.append(SentenceEncoderMatcher("sentence-transformers/LaBSE", name="labse"))
        matchers.append(SentenceEncoderMatcher("google/muril-base-cased", name="muril"))
    if _HAVE_ANTHROPIC and os.environ.get("ANTHROPIC_API_KEY"):
        matchers.append(LLMRerankerMatcher())
    return matchers


def unavailable() -> dict[str, str]:
    """Why each neural matcher is absent, for the results header."""
    out: dict[str, str] = {}
    if not _HAVE_SKLEARN:
        out["char_embedding_svd"] = "scikit-learn not installed"
    if not _HAVE_SENTENCE_TRANSFORMERS:
        out["labse, muril"] = (
            "sentence-transformers not installed "
            "(pip install indic-name-bench[neural]); model weights also require "
            "network access to huggingface.co"
        )
    elif not os.environ.get("INDIC_BENCH_ENABLE_ENCODERS"):
        out["labse, muril"] = (
            "installed but disabled; set INDIC_BENCH_ENABLE_ENCODERS=1 to download "
            "and run them"
        )
    if not _HAVE_ANTHROPIC:
        out["llm_reranker"] = "anthropic SDK not installed (pip install indic-name-bench[llm])"
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        out["llm_reranker"] = "ANTHROPIC_API_KEY not set"
    return out
