"""Website agent — manages the author's WordPress website via REST API."""
import os
import re
import json
import base64
import anthropic
import requests
from anthropic import beta_tool
from author_config import (
    MODEL, MAX_TOKENS,
    WORDPRESS_URL, WORDPRESS_USER, WORDPRESS_APP_PASSWORD,
    WEBSITE_DIR, AUTHOR_PEN_NAME,
)

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an author website manager who keeps the site fresh,
engaging, and optimized to sell books and grow the author's email list.

Pages and content you manage:
- **Blog posts** — writing tips, behind-the-scenes, reader updates, announcements
- **Book pages** — description, excerpt, buy links, reviews
- **Newsletter / opt-in** — lead magnet copy, landing page copy
- **Author bio** — short and long versions
- **Events** — signings, readings, virtual appearances

Best practices:
- Every post ends with a CTA (newsletter signup, book link, or comment prompt)
- SEO: include focus keyword in title, first paragraph, and headings
- Blog posts: 600–1500 words is ideal for author blogs
- Book pages: include genre, age range, content warnings if relevant

When writing content, always save drafts locally before publishing.
Use update_page for static pages, create_post for blog posts."""


def _wp_headers() -> dict:
    if not (WORDPRESS_USER and WORDPRESS_APP_PASSWORD):
        return {}
    creds = base64.b64encode(
        f"{WORDPRESS_USER}:{WORDPRESS_APP_PASSWORD}".encode()
    ).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def _wp_request(method: str, path: str, **kwargs) -> dict:
    """Make a WordPress REST API request."""
    if not WORDPRESS_URL:
        return {"error": "WORDPRESS_URL not configured in .env"}
    headers = _wp_headers()
    if not headers:
        return {"error": "WORDPRESS_USER or WORDPRESS_APP_PASSWORD not configured in .env"}
    url = f"{WORDPRESS_URL.rstrip('/')}/wp-json/wp/v2/{path}"
    response = getattr(requests, method)(url, headers=headers, **kwargs)
    try:
        return response.json()
    except Exception:
        return {"error": response.text, "status_code": response.status_code}


@beta_tool
def get_recent_posts(count: int = 10) -> str:
    """Get recent blog posts from the author website.

    Args:
        count: Number of posts to retrieve
    """
    data = _wp_request("get", f"posts?per_page={min(count, 20)}&_fields=id,title,status,date,link")
    return json.dumps(data, indent=2)


@beta_tool
def get_pages() -> str:
    """Get all static pages on the author website."""
    data = _wp_request("get", "pages?_fields=id,title,status,link")
    return json.dumps(data, indent=2)


@beta_tool
def create_post(
    title: str,
    content: str,
    status: str = "draft",
    categories: str = "",
    tags: str = "",
    excerpt: str = "",
) -> str:
    """Create a new blog post on the author website.

    Args:
        title: Post title
        content: Post content in HTML format
        status: 'draft' (default) or 'publish'
        categories: Comma-separated category names or IDs
        tags: Comma-separated tag names
        excerpt: Short excerpt/teaser (plain text)
    """
    payload: dict = {
        "title": title,
        "content": content,
        "status": status,
        "excerpt": excerpt,
    }
    result = _wp_request("post", "posts", json=payload)
    # Also save locally
    _save_website_draft(title, content, "post")
    return json.dumps(result, indent=2)


@beta_tool
def update_page(page_id: int, title: str = "", content: str = "", status: str = "") -> str:
    """Update an existing static page on the author website.

    Args:
        page_id: WordPress page ID
        title: New page title (leave empty to keep current)
        content: New page content in HTML (leave empty to keep current)
        status: New status — 'publish', 'draft', etc.
    """
    payload: dict = {}
    if title:
        payload["title"] = title
    if content:
        payload["content"] = content
        _save_website_draft(title or f"page_{page_id}", content, "page")
    if status:
        payload["status"] = status
    if not payload:
        return json.dumps({"error": "No fields provided to update"})
    result = _wp_request("post", f"pages/{page_id}", json=payload)
    return json.dumps(result, indent=2)


@beta_tool
def save_draft(title: str, content: str, content_type: str = "post") -> str:
    """Save a local draft before publishing (does not post to website).

    Args:
        title: Title of the draft
        content: Full content
        content_type: 'post', 'page', or 'bio'
    """
    _save_website_draft(title, content, content_type)
    return json.dumps({"saved": True, "title": title, "type": content_type})


def _save_website_draft(title: str, content: str, content_type: str) -> str:
    filename = re.sub(r"[^\w\-]", "_", title.lower()[:60]) + f"_{content_type}.html"
    path = os.path.join(WEBSITE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- {title} -->\n{content}")
    return path


@beta_tool
def list_drafts() -> str:
    """List locally saved website drafts."""
    files = sorted(os.listdir(WEBSITE_DIR))
    return json.dumps({"drafts": files, "count": len(files)})


@beta_tool
def read_draft(filename: str) -> str:
    """Read a locally saved website draft.

    Args:
        filename: Filename from list_drafts
    """
    path = os.path.join(WEBSITE_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return json.dumps({"error": f"Draft '{filename}' not found"})


@beta_tool
def generate_seo_metadata(title: str, content_summary: str, focus_keyword: str) -> str:
    """Generate SEO metadata for a page or post.

    Args:
        title: Page or post title
        content_summary: Brief summary of what the content covers
        focus_keyword: Target keyword for this page
    """
    prompt = (
        f"Generate SEO metadata for an author website page:\n"
        f"Title: {title}\n"
        f"Content: {content_summary}\n"
        f"Focus keyword: {focus_keyword}\n\n"
        f"Provide:\n"
        f"1. SEO title (60 chars max, include keyword)\n"
        f"2. Meta description (155 chars max, include keyword, compelling)\n"
        f"3. 5 related long-tail keywords\n"
        f"4. Suggested URL slug\n"
        f"Return as JSON."
    )
    seo_client = anthropic.Anthropic()
    response = seo_client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return next((b.text for b in response.content if b.type == "text"), "{}")


def run(task: str) -> str:
    """Run the website agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[
            get_recent_posts, get_pages, create_post, update_page,
            save_draft, list_drafts, read_draft, generate_seo_metadata,
        ],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from website agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Website task completed."
