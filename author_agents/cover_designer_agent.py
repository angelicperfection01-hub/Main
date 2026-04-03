"""Cover designer agent — creates book cover briefs and AI image generation prompts."""
import os
import re
import json
import anthropic
from anthropic import beta_tool
from author_config import MODEL, MAX_TOKENS, COVERS_DIR, OUTLINES_DIR, MANUSCRIPTS_DIR

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a professional book cover designer with deep knowledge of
genre conventions, typography, and visual storytelling. You create comprehensive
cover briefs and AI image generation prompts.

For every cover design, you produce:
1. **Design Brief** — genre analysis, mood, color palette, typography direction,
   imagery concepts, comparable titles ("comp covers")
2. **Midjourney Prompt** — detailed /imagine prompt optimized for book covers
3. **DALL-E Prompt** — alternative prompt for OpenAI image generation
4. **Back Cover Copy** — compelling blurb (150–200 words) plus author bio placeholder
5. **Spine Design Notes** — title, author name sizing for the spine

Genre rules to follow:
- Thriller/Mystery: dark tones, fragmented imagery, bold sans-serif
- Romance: warm palette, couple silhouettes or flowers, elegant serif
- Fantasy/Sci-Fi: epic landscapes, dramatic lighting, illustrated style
- Self-Help/Business: clean, minimalist, bold typography-forward
- Literary Fiction: artistic, abstract, painterly quality

Always read the book outline or manuscript summary before designing."""


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:80]


@beta_tool
def read_outline(book_title: str) -> str:
    """Read the outline for a book to inform cover design.

    Args:
        book_title: The title of the book
    """
    filename = _safe_filename(book_title) + ".md"
    path = os.path.join(OUTLINES_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return json.dumps({"error": f"No outline found for '{book_title}'"})


@beta_tool
def read_manuscript_summary(book_title: str) -> str:
    """Read available manuscript chapters to understand the book.

    Args:
        book_title: The title of the book
    """
    book_dir = os.path.join(MANUSCRIPTS_DIR, _safe_filename(book_title))
    if not os.path.exists(book_dir):
        return json.dumps({"error": f"No manuscript found for '{book_title}'"})
    chapters = sorted(f for f in os.listdir(book_dir) if f.endswith(".md")
                      and not f.startswith("_"))[:3]  # first 3 chapters
    combined = []
    for ch in chapters:
        path = os.path.join(book_dir, ch)
        with open(path, encoding="utf-8") as f:
            combined.append(f"## {ch}\n" + f.read()[:2000])  # first 2000 chars per chapter
    return "\n\n---\n\n".join(combined) if combined else json.dumps({"error": "No chapters found"})


@beta_tool
def save_cover_brief(
    book_title: str,
    design_brief: str,
    midjourney_prompt: str,
    dalle_prompt: str,
    back_cover_copy: str,
    spine_notes: str,
) -> str:
    """Save the complete cover design package to disk.

    Args:
        book_title: The title of the book
        design_brief: Full design brief with mood, palette, typography, comps
        midjourney_prompt: Optimized /imagine prompt for Midjourney
        dalle_prompt: Alternative prompt for DALL-E
        back_cover_copy: Back cover blurb (150-200 words)
        spine_notes: Typography and sizing notes for the spine
    """
    filename = _safe_filename(book_title) + "_cover_brief.md"
    path = os.path.join(COVERS_DIR, filename)
    content = f"""# Cover Design Package: {book_title}

## Design Brief
{design_brief}

## Midjourney Prompt
```
{midjourney_prompt}
```

## DALL-E Prompt
```
{dalle_prompt}
```

## Back Cover Copy
{back_cover_copy}

## Spine Design Notes
{spine_notes}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return json.dumps({"saved": path, "book_title": book_title})


@beta_tool
def list_cover_briefs() -> str:
    """List all saved cover design briefs."""
    files = sorted(f for f in os.listdir(COVERS_DIR) if f.endswith(".md"))
    return json.dumps({"cover_briefs": files, "count": len(files)})


@beta_tool
def read_cover_brief(book_title: str) -> str:
    """Read a saved cover brief.

    Args:
        book_title: The title of the book
    """
    filename = _safe_filename(book_title) + "_cover_brief.md"
    path = os.path.join(COVERS_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return json.dumps({"error": f"No cover brief found for '{book_title}'"})


def run(task: str) -> str:
    """Run the cover designer agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[read_outline, read_manuscript_summary, save_cover_brief,
               list_cover_briefs, read_cover_brief],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from cover designer agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Cover design completed."
