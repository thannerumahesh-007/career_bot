"""
Text Sanitizer and Response Cleaning Layer for CareerBot.
1. clean_chat_response(): Cleans raw Markdown symbols (###, **, *, \\), stray backslashes,
   and model artifacts into clean, readable formatting with bullet points and clear headings.
2. clean_text_for_tts(): Prepares text for natural speech synthesis (ElevenLabs / Web Speech API).
"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_chat_response(text: str) -> str:
    """
    Cleans raw model formatting artifacts from user-facing AI Assistant responses.
    Eliminates raw ###, **, stray backslashes (\\), and malformed symbols while preserving
    clean bullet points, numbered lists, paragraph spacing, and legible emphasis.
    """
    if not text:
        return ""

    cleaned = text

    # 1. Remove escaped backslashes (e.g., \* -> *, \_ -> _, \# -> #, \- -> -)
    cleaned = re.sub(r"\\([*_#`~\\+-\[\]\(\)])", r"\1", cleaned)

    # 2. Convert markdown headers (### Header -> Header:\n or clean bold title)
    cleaned = re.sub(r"(?m)^#{1,6}\s*(.+?)\s*$", r"\1:", cleaned)

    # 3. Clean bold/italic asterisks:
    # First, handle bullet items like "• **Python:** desc" -> "• Python: desc" or keep clean
    cleaned = re.sub(r"\*{2,3}(.+?)\*{2,3}", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\w)\*([^\*\n]+?)\*(?!\w)", r"\1", cleaned)
    cleaned = re.sub(r"_{2,3}(.+?)_{2,3}", r"\1", cleaned)

    # 4. Standardize bullet points (*, -, + at start of line -> •)
    cleaned = re.sub(r"(?m)^\s*[-*+►]\s+", "• ", cleaned)

    # 5. Clean stray leading or trailing asterisks and hash marks
    cleaned = re.sub(r"(?m)^\s*#+\s*", "", cleaned)
    cleaned = re.sub(r"\*{2,}", "", cleaned)

    # 6. Remove unnecessary code blocks wrapping regular text prose
    cleaned = re.sub(r"```(?:\w+)?\n([\s\S]*?)```", r"\1", cleaned)
    cleaned = re.sub(r"`([^`\n]+)`", r"\1", cleaned)

    # 7. Remove markdown link brackets [Text](url) -> Text (url) or just Text if anchor is '#'
    cleaned = re.sub(r"\[([^\]]+)\]\(#\)", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1 (\2)", cleaned)

    # 8. Remove duplicate punctuation and stray backslashes
    cleaned = cleaned.replace("\\", "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # 9. Clean up any duplicated colons resulting from header conversion (e.g., "Title::" -> "Title:")
    cleaned = re.sub(r":{2,}", ":", cleaned)

    return cleaned.strip()


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

    # 11. Remove decorative symbols but preserve hyphens in words, apostrophes, and basic punctuation
    cleaned = re.sub(r"[*#~`_\\/|<>{}[\]]", " ", cleaned)

    # 12. Normalize multiple punctuation and spacing
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r" +([.,!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
