"""KDP agent — prepares manuscripts and metadata for Amazon Kindle Direct Publishing."""
import os
import re
import json
import anthropic
from anthropic import beta_tool
from author_config import (
    MODEL, MAX_TOKENS, MANUSCRIPTS_DIR, COVERS_DIR,
    AUTHOR_PEN_NAME, KDP_EMAIL,
)

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert in Amazon KDP (Kindle Direct Publishing) self-publishing.
You help authors prepare and upload their books correctly to maximize discoverability
and royalties.

Your expertise covers:
- KDP metadata optimization (title, subtitle, keywords, categories)
- BISAC category selection for maximum visibility
- Pricing strategy (eBook vs. paperback, KDP Select vs. wide)
- Book description / A+ content copywriting (HTML-formatted for KDP)
- ISBN requirements and pricing
- Print-on-demand specifications (trim size, bleed, margins, spine width)
- KDP keyword research (7 keywords, long-tail strategy)
- Series setup and series page optimization
- Pre-order strategy

When preparing a KDP upload package, always include all fields KDP requires.
Note: Amazon does not have a public KDP API — provide a complete checklist and
formatted data the author can copy-paste into KDP directly."""


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:80]


def _book_dir(book_title: str) -> str:
    return os.path.join(MANUSCRIPTS_DIR, _safe_filename(book_title))


@beta_tool
def list_books() -> str:
    """List books with completed or in-progress manuscripts."""
    books = sorted(d for d in os.listdir(MANUSCRIPTS_DIR)
                   if os.path.isdir(os.path.join(MANUSCRIPTS_DIR, d)))
    return json.dumps({"books": books})


@beta_tool
def get_manuscript_info(book_title: str) -> str:
    """Get word count and chapter info for a manuscript.

    Args:
        book_title: The title of the book
    """
    book_dir = _book_dir(book_title)
    if not os.path.exists(book_dir):
        return json.dumps({"error": f"No manuscript found for '{book_title}'"})
    total_words = 0
    chapters = []
    for f in sorted(os.listdir(book_dir)):
        if f.endswith(".md") and not f.startswith("_"):
            path = os.path.join(book_dir, f)
            with open(path, encoding="utf-8") as fh:
                words = len(fh.read().split())
            chapters.append({"chapter": f, "words": words})
            total_words += words
    return json.dumps({
        "book_title": book_title,
        "total_words": total_words,
        "chapter_count": len(chapters),
        "chapters": chapters,
        "estimated_pages_paperback": round(total_words / 250),
    })


@beta_tool
def read_cover_brief(book_title: str) -> str:
    """Read the cover brief to pull back cover copy for KDP description.

    Args:
        book_title: The title of the book
    """
    filename = _safe_filename(book_title) + "_cover_brief.md"
    path = os.path.join(COVERS_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return json.dumps({"error": f"No cover brief found for '{book_title}'"})


@beta_tool
def save_kdp_package(
    book_title: str,
    subtitle: str,
    series_name: str,
    series_number: str,
    author_name: str,
    description_html: str,
    keywords: str,
    bisac_primary: str,
    bisac_secondary: str,
    kdp_categories: str,
    price_ebook_usd: str,
    price_paperback_usd: str,
    trim_size: str,
    page_count_estimate: str,
    language: str,
    is_kdp_select: str,
    upload_checklist: str,
) -> str:
    """Save the complete KDP upload package to disk.

    Args:
        book_title: Full book title
        subtitle: Subtitle (leave empty if none)
        series_name: Series name if part of a series
        series_number: Series number e.g. '1'
        author_name: Author or pen name
        description_html: Book description formatted with HTML tags (<b>, <br>, etc.)
        keywords: 7 comma-separated keywords/phrases for KDP
        bisac_primary: Primary BISAC category code e.g. 'FIC002000'
        bisac_secondary: Secondary BISAC category code
        kdp_categories: Two KDP browse categories (path format)
        price_ebook_usd: Recommended eBook price e.g. '4.99'
        price_paperback_usd: Recommended paperback price e.g. '14.99'
        trim_size: Paperback trim size e.g. '6 x 9 inches'
        page_count_estimate: Estimated page count
        language: Language e.g. 'English'
        is_kdp_select: 'Yes' or 'No' for KDP Select enrollment
        upload_checklist: Step-by-step upload checklist in markdown
    """
    filename = _safe_filename(book_title) + "_kdp_package.md"
    kdp_dir = os.path.join(MANUSCRIPTS_DIR, _safe_filename(book_title))
    os.makedirs(kdp_dir, exist_ok=True)
    path = os.path.join(kdp_dir, filename)

    content = f"""# KDP Upload Package: {book_title}

## Bibliographic Information
| Field | Value |
|-------|-------|
| **Title** | {book_title} |
| **Subtitle** | {subtitle} |
| **Series Name** | {series_name} |
| **Series Number** | {series_number} |
| **Author** | {author_name} |
| **Language** | {language} |
| **KDP Select** | {is_kdp_select} |

## Book Description (HTML for KDP)
```html
{description_html}
```

## Keywords (7 max)
{keywords}

## Categories
**BISAC Primary:** {bisac_primary}
**BISAC Secondary:** {bisac_secondary}
**KDP Browse Categories:**
{kdp_categories}

## Pricing
| Format | Price |
|--------|-------|
| eBook | ${price_ebook_usd} |
| Paperback | ${price_paperback_usd} |

## Print Specifications
| Field | Value |
|-------|-------|
| **Trim Size** | {trim_size} |
| **Estimated Pages** | {page_count_estimate} |

## Upload Checklist
{upload_checklist}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return json.dumps({"saved": path, "book_title": book_title})


def run(task: str) -> str:
    """Run the KDP agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[list_books, get_manuscript_info, read_cover_brief, save_kdp_package],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from KDP agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "KDP package prepared."
