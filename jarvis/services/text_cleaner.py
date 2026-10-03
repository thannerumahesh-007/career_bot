import re
import logging

logger = logging.getLogger(__name__)


def clean_text_for_tts(text: str) -> str:
    """
    Cleans and prepares text specifically for natural ElevenLabs speech synthesis.
    Converts lists, Markdown, and symbols into fluent conversational spoken English.
    Preserves meaning, real words, and word hyphens (e.g. object-oriented).
    """
    if not text:
        return ""

    cleaned = text

    # 1. Remove code blocks (fences) but retain inner code content for natural reading
    cleaned = re.sub(r"```(?:[\w]*\n)?([\s\S]*?)```", r"\1", cleaned)

    # 2. Inline code backticks `code` -> code
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # 3. Markdown images ![alt](url) -> ""
    cleaned = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"", cleaned)

    # 4. Markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

    # 5. Remove horizontal rules (---, ___, ***)
    cleaned = re.sub(r"(?m)^[-*_]{3,}\s*$", "", cleaned)

    # 6. Convert Markdown headers # Header -> Header. (adds sentence pause)
    cleaned = re.sub(r"(?m)^#{1,6}\s*(.+?)\s*$", r"\1.", cleaned)

    # 7. Convert blockquotes > quote -> quote
    cleaned = re.sub(r"(?m)^>\s*", "", cleaned)

    # 8. Convert numbered lists at start of line into natural conversational transitions
    ordinals = {
        "1": "First,",
        "2": "Second,",
        "3": "Third,",
        "4": "Fourth,",
        "5": "Fifth,",
        "6": "Sixth,",
        "7": "Seventh,",
        "8": "Eighth,",
        "9": "Ninth,",
        "10": "Tenth,",
    }

    def replace_num(match):
        num = match.group(1)
        return ordinals.get(num, "Additionally,") + " "

    cleaned = re.sub(r"(?m)^\s*(\d{1,2})\.\s+", replace_num, cleaned)

    # 9. Convert bullet characters at line start
    cleaned = re.sub(r"(?m)^\s*[-*+•►]\s+", "", cleaned)

    # 10. Remove bold, italic, and strikethrough markers
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.+?)\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.+?)__", r"\1", cleaned)
    cleaned = re.sub(r"_(.+?)_", r"\1", cleaned)
    cleaned = re.sub(r"~~(.+?)~~", r"\1", cleaned)

    # 11. Remove any remaining stray markdown/formatting symbols but preserve hyphens in words and apostrophes
    cleaned = re.sub(r"[*#~`_\\/|<>{}[\]]", " ", cleaned)

    # 12. Normalize multiple punctuation and spacing
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r" +([.,!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
