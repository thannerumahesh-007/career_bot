"""
Text Preprocessing Pipeline for CareerBot using NLTK (with graceful fallback).
Performs cleaning, lowercasing, tokenization, stop-word removal, and lemmatization.
"""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Ensure NLTK data dependencies are loaded silently
def _ensure_nltk_data():
    resources = [
        ('corpora/stopwords', 'stopwords'),
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/wordnet', 'wordnet')
    ]
    for res_path, res_name in resources:
        try:
            nltk.data.find(res_path)
        except LookupError:
            try:
                nltk.download(res_name, quiet=True)
            except Exception:
                pass

_ensure_nltk_data()

_lemmatizer = WordNetLemmatizer()

try:
    _stop_words = set(stopwords.words('english'))
except Exception:
    _stop_words = {
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'you', 'your', 'yours',
        'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they', 'them', 'their',
        'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but',
        'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for',
        'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on',
        'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
        'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
    }


def clean_text(text: str) -> str:
    """Cleans text by removing non-alphanumeric noise (preserving tech punctuation like C++, C#, .js)."""
    if not text:
        return ""
    # Retain characters useful for tech skills: +, #, ., -
    text_clean = re.sub(r'[^\w\s\+#\.-]', ' ', str(text))
    return text_clean.strip()


def tokenize(text: str) -> list:
    """Tokenizes text into words."""
    cleaned = clean_text(text)
    if not cleaned:
        return []
    try:
        tokens = word_tokenize(cleaned.lower())
    except Exception:
        tokens = cleaned.lower().split()
    return tokens


def remove_stopwords(tokens: list) -> list:
    """Filters out English stop words."""
    return [t for t in tokens if t not in _stop_words and len(t) > 1]


def lemmatize(tokens: list) -> list:
    """Lemmatizes tokens into standard base form."""
    return [_lemmatizer.lemmatize(t) for t in tokens]


def preprocess_text(text: str) -> str:
    """Full preprocessing pipeline returning clean space-separated text."""
    tokens = tokenize(text)
    filtered = remove_stopwords(tokens)
    lemmatized = lemmatize(filtered)
    return " ".join(lemmatized)
