"""Writer agent — drafts book content chapter by chapter based on the outline."""
import os
import re
import json
import anthropic
from anthropic import beta_tool
from author_config import MODEL, MAX_TOKENS, OUTLINES_DIR, MANUSCRIPTS_DIR

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a skilled ghostwriter who produces vivid, engaging prose
in whatever genre and voice the author needs. You write full chapters, not summaries.

Guidelines:
- Follow the outline closely but let the writing breathe naturally
- Match the requested tone: literary, commercial, conversational, etc.
- Use strong opening lines that hook the reader immediately
- Show, don't tell — use scenes, dialogue, and sensory detail
- Keep chapters focused on their outlined purpose
- End chapters with a reason to turn the page

Always read the outline before writing. Save each chapter as you complete it."""


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:80]


def _book_dir(book_title: str) -> str:
    path = os.path.join(MANUSCRIPTS_DIR, _safe_filename(book_title))
    os.makedirs(path, exist_ok=True)
    return path


@beta_tool
def read_outline(book_title: str) -> str:
    """Read the outline for a book.

    Args:
        book_title: The title of the book
    """
    filename = _safe_filename(book_title) + ".md"
    path = os.path.join(OUTLINES_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    files = os.listdir(OUTLINES_DIR)
    return json.dumps({"error": f"No outline found for '{book_title}'", "available": files})


@beta_tool
def list_outlines() -> str:
    """List all available book outlines."""
    files = sorted(f for f in os.listdir(OUTLINES_DIR) if f.endswith(".md"))
    return json.dumps({"outlines": files})


@beta_tool
def save_chapter(book_title: str, chapter_name: str, content: str) -> str:
    """Save a written chapter to disk.

    Args:
        book_title: The title of the book
        chapter_name: Chapter identifier, e.g. 'chapter_01' or 'prologue'
        content: Full written chapter content
    """
    book_dir = _book_dir(book_title)
    filename = _safe_filename(chapter_name) + ".md"
    path = os.path.join(book_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {chapter_name}\n\n{content}")
    word_count = len(content.split())
    return json.dumps({"saved": path, "chapter": chapter_name, "word_count": word_count})


@beta_tool
def read_chapter(book_title: str, chapter_name: str) -> str:
    """Read a previously written chapter.

    Args:
        book_title: The title of the book
        chapter_name: Chapter identifier to read
    """
    book_dir = _book_dir(book_title)
    filename = _safe_filename(chapter_name) + ".md"
    path = os.path.join(book_dir, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return json.dumps({"error": f"Chapter '{chapter_name}' not found in {book_title}"})


@beta_tool
def list_chapters(book_title: str) -> str:
    """List all written chapters for a book.

    Args:
        book_title: The title of the book
    """
    book_dir = _book_dir(book_title)
    files = sorted(f for f in os.listdir(book_dir) if f.endswith(".md"))
    total_words = 0
    chapters = []
    for f in files:
        path = os.path.join(book_dir, f)
        with open(path, encoding="utf-8") as fh:
            words = len(fh.read().split())
        chapters.append({"file": f, "word_count": words})
        total_words += words
    return json.dumps({"chapters": chapters, "total_word_count": total_words})


@beta_tool
def get_manuscript_stats(book_title: str) -> str:
    """Get word count and progress stats for a manuscript.

    Args:
        book_title: The title of the book
    """
    return list_chapters(book_title)


def run(task: str) -> str:
    """Run the writer agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[read_outline, list_outlines, save_chapter, read_chapter,
               list_chapters, get_manuscript_stats],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from writer agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Writing completed."
