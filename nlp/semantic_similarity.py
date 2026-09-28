"""
Semantic Similarity Calculator using TF-IDF and Cosine Similarity.
Provides normalized [0.0, 1.0] score comparing user profile text with job descriptions.
Includes pure-Python fallback to ensure stability when C-extension DLLs (e.g. Scipy/Sklearn)
are restricted by OS Application Control policies.
"""

import math
import re
from collections import Counter
from nlp.preprocessing import preprocess_text

# Safe import of scikit-learn with pure-Python fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


def _pure_python_tfidf_cosine_similarity(text1: str, text2: str) -> float:
    """Pure-Python TF-IDF and Cosine Similarity calculation."""
    tokens1 = re.findall(r'\b\w+\b', text1.lower())
    tokens2 = re.findall(r'\b\w+\b', text2.lower())

    if not tokens1 or not tokens2:
        return 0.0

    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)
    
    len1 = len(tokens1)
    len2 = len(tokens2)

    all_words = set(tf1.keys()).union(set(tf2.keys()))
    if not all_words:
        return 0.0

    # Calculate IDF across the 2 document corpus
    idf = {}
    for word in all_words:
        doc_freq = (1 if word in tf1 else 0) + (1 if word in tf2 else 0)
        # Smoothing formula: ln((1 + N) / (1 + df)) + 1
        idf[word] = math.log((1.0 + 2.0) / (1.0 + doc_freq)) + 1.0

    # Build TF-IDF vectors
    v1 = {w: (tf1[w] / float(len1)) * idf[w] for w in tf1}
    v2 = {w: (tf2[w] / float(len2)) * idf[w] for w in tf2}

    # Cosine similarity dot product
    dot_product = sum(v1[w] * v2.get(w, 0.0) for w in v1)
    mag1 = math.sqrt(sum(val ** 2 for val in v1.values()))
    mag2 = math.sqrt(sum(val ** 2 for val in v2.values()))

    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0

    score = dot_product / (mag1 * mag2)
    return float(max(0.0, min(1.0, score)))


class SemanticSimilarityEngine:
    """Calculates TF-IDF cosine similarity between user profile and job posting."""

    def calculate_similarity(self, user_text: str, job_text: str) -> float:
        """Computes normalized cosine similarity in range [0.0, 1.0]."""
        if not user_text or not job_text:
            return 0.0

        user_clean = preprocess_text(user_text)
        job_clean = preprocess_text(job_text)

        if not user_clean.strip() or not job_clean.strip():
            return 0.0

        if SKLEARN_AVAILABLE:
            try:
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform([user_clean, job_clean])
                score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(max(0.0, min(1.0, score)))
            except Exception:
                pass

        # Fallback to pure-Python engine if sklearn is unavailable or fails due to OS DLL block
        return _pure_python_tfidf_cosine_similarity(user_clean, job_clean)
