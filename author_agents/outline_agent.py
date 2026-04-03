"""Outline agent — creates structured book outlines from research."""
import os
import re
import json
import anthropic
from anthropic import beta_tool
from author_config import MODEL, MAX_TOKENS, RESEARCH_DIR, OUTLINES_DIR

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert book outline architect. You create compelling,
well-structured outlines for books of any genre — fiction, non-fiction, self-help,
memoir, thriller, and more.

A great outline includes:
- A hook-driven opening chapter or prologue concept
- Clear narrative or informational arc
- Chapter-by-chapter breakdown with purpose and key content
- Character arcs (fiction) or key arguments (non-fiction) threaded through
- Pacing notes — where tension rises, where the reader breathes
- A satisfying conclusion strategy

Read any available research before outlining. Always save the final outline."""


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:80]


@beta_tool
def read_research(topic: str) -> str:
    """Read saved research for a topic.

    Args:
        topic: Topic or filename to look up in the research directory
    """
    filename = _safe_filename(topic)
    for candidate in (filename + ".md", topic if topic.endswith(".md") else None):
        if candidate:
            path = os.path.join(RESEARCH_DIR, candidate)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return f.read()
    files = os.listdir(RESEARCH_DIR)
    return json.dumps({"error": f"No research found for '{topic}'", "available": files})


@beta_tool
def list_research() -> str:
    """List all available research files."""
    files = sorted(f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md"))
    return json.dumps({"research_files": files, "count": len(files)})


@beta_tool
def save_outline(book_title: str, outline: str) -> str:
    """Save a book outline to disk.

    Args:
        book_title: The working title of the book (used as filename)
        outline: Full outline content in markdown format
    """
    filename = _safe_filename(book_title) + ".md"
    path = os.path.join(OUTLINES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Outline: {book_title}\n\n{outline}")
    return json.dumps({"saved": path, "book_title": book_title})


@beta_tool
def read_outline(book_title: str) -> str:
    """Read a saved outline.

    Args:
        book_title: Title or filename of the book outline
    """
    filename = _safe_filename(book_title)
    for candidate in (filename + ".md", book_title if book_title.endswith(".md") else None):
        if candidate:
            path = os.path.join(OUTLINES_DIR, candidate)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return f.read()
    files = os.listdir(OUTLINES_DIR)
    return json.dumps({"error": f"No outline found for '{book_title}'", "available": files})


@beta_tool
def list_outlines() -> str:
    """List all saved book outlines."""
    files = sorted(f for f in os.listdir(OUTLINES_DIR) if f.endswith(".md"))
    return json.dumps({"outlines": files, "count": len(files)})


def run(task: str) -> str:
    """Run the outline agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[read_research, list_research, save_outline, read_outline, list_outlines],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from outline agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Outline completed."
