"""Editor agent — proofreads, improves, and polishes manuscript chapters."""
import os
import re
import json
import anthropic
from anthropic import beta_tool
from author_config import MODEL, MAX_TOKENS, MANUSCRIPTS_DIR

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a professional book editor with decades of experience across
all genres. You improve manuscripts while preserving the author's voice.

Your editing covers:
- **Line editing**: sentence flow, word choice, clarity, rhythm
- **Copy editing**: grammar, punctuation, consistency, spelling
- **Developmental notes**: pacing, structure, character consistency (flag don't rewrite)
- **Continuity checks**: catch contradictions with earlier chapters when possible

When editing:
1. Read the chapter fully before making changes
2. Edit in place — return the full improved text, not a diff
3. Add a brief editor's note at the top summarizing key changes made
4. Flag any developmental concerns as [EDITOR NOTE: ...] inline

Do not change the author's voice or sanitize distinctive stylistic choices."""


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:80]


def _book_dir(book_title: str) -> str:
    return os.path.join(MANUSCRIPTS_DIR, _safe_filename(book_title))


@beta_tool
def list_books() -> str:
    """List all books with manuscripts in progress."""
    books = [d for d in os.listdir(MANUSCRIPTS_DIR)
             if os.path.isdir(os.path.join(MANUSCRIPTS_DIR, d))]
    return json.dumps({"books": sorted(books)})


@beta_tool
def list_chapters(book_title: str) -> str:
    """List chapters for a book.

    Args:
        book_title: The title of the book
    """
    book_dir = _book_dir(book_title)
    if not os.path.exists(book_dir):
        return json.dumps({"error": f"No manuscript directory found for '{book_title}'"})
    files = sorted(f for f in os.listdir(book_dir) if f.endswith(".md"))
    return json.dumps({"chapters": files})


@beta_tool
def read_chapter(book_title: str, chapter_name: str) -> str:
    """Read a chapter from the manuscript.

    Args:
        book_title: The title of the book
        chapter_name: Chapter filename (with or without .md)
    """
    book_dir = _book_dir(book_title)
    filename = _safe_filename(chapter_name)
    for candidate in (filename + ".md", chapter_name):
        path = os.path.join(book_dir, candidate)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    return json.dumps({"error": f"Chapter '{chapter_name}' not found"})


@beta_tool
def save_edited_chapter(book_title: str, chapter_name: str, edited_content: str) -> str:
    """Save an edited chapter, overwriting the original.

    Args:
        book_title: The title of the book
        chapter_name: Chapter to overwrite with edited version
        edited_content: Full edited chapter text (including editor's note at top)
    """
    book_dir = _book_dir(book_title)
    if not os.path.exists(book_dir):
        return json.dumps({"error": f"Manuscript directory not found for '{book_title}'"})
    filename = _safe_filename(chapter_name) + ".md"
    path = os.path.join(book_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(edited_content)
    word_count = len(edited_content.split())
    return json.dumps({"saved": path, "word_count": word_count})


@beta_tool
def save_edit_notes(book_title: str, notes: str) -> str:
    """Save overall editorial notes for the book (developmental feedback).

    Args:
        book_title: The title of the book
        notes: Editor's overall notes in markdown
    """
    book_dir = _book_dir(book_title)
    if not os.path.exists(book_dir):
        return json.dumps({"error": f"Manuscript directory not found for '{book_title}'"})
    path = os.path.join(book_dir, "_editorial_notes.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Editorial Notes: {book_title}\n\n{notes}")
    return json.dumps({"saved": path})


def run(task: str) -> str:
    """Run the editor agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[list_books, list_chapters, read_chapter, save_edited_chapter, save_edit_notes],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from editor agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Editing completed."
