"""Instagram agent — manages the author's Instagram account via Meta Graph API."""
import os
import re
import json
import anthropic
import requests
from anthropic import beta_tool
from author_config import (
    MODEL, MAX_TOKENS,
    INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID,
    MANUSCRIPTS_DIR, COVERS_DIR,
)

_client = anthropic.Anthropic()

_IG_BASE = "https://graph.facebook.com/v19.0"

SYSTEM_PROMPT = """You are a savvy social media manager specializing in author branding
on Instagram. You understand how to grow an author's audience, sell books, and build
community through authentic content.

Content pillars for authors:
1. **Book content** — quotes, chapter reveals, cover reveals, launch countdowns
2. **Behind the scenes** — writing process, research trips, workspace
3. **Reader engagement** — polls, questions, reading recommendations
4. **Personal brand** — who the author is, their story, values
5. **Promotional** — book links, reviews, sale announcements (max 20% of posts)

Caption rules:
- Hook in the first line (before "more" fold)
- Emojis used tastefully to break up text
- Relevant hashtags (15–20) in the first comment or end of caption
- Call to action on every post
- Authentic, conversational tone

Always draft captions before posting. Use schedule_post for planned content."""


def _ig_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make a Meta Graph API request."""
    if not INSTAGRAM_ACCESS_TOKEN:
        return {"error": "INSTAGRAM_ACCESS_TOKEN not configured in .env"}
    url = f"{_IG_BASE}/{endpoint}"
    params = kwargs.pop("params", {})
    params["access_token"] = INSTAGRAM_ACCESS_TOKEN
    response = getattr(requests, method)(url, params=params, **kwargs)
    try:
        return response.json()
    except Exception:
        return {"error": response.text, "status_code": response.status_code}


@beta_tool
def get_account_info() -> str:
    """Get the Instagram business account profile info."""
    if not INSTAGRAM_ACCOUNT_ID:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID not set in .env"})
    data = _ig_request(
        "get",
        INSTAGRAM_ACCOUNT_ID,
        params={"fields": "username,name,biography,followers_count,follows_count,media_count,profile_picture_url"}
    )
    return json.dumps(data, indent=2)


@beta_tool
def get_recent_posts(limit: int = 10) -> str:
    """Get recent Instagram posts with engagement stats.

    Args:
        limit: Number of recent posts to retrieve (max 25)
    """
    if not INSTAGRAM_ACCOUNT_ID:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID not set in .env"})
    data = _ig_request(
        "get",
        f"{INSTAGRAM_ACCOUNT_ID}/media",
        params={
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit": min(limit, 25),
        }
    )
    return json.dumps(data, indent=2)


@beta_tool
def get_insights(period: str = "day") -> str:
    """Get account insights (reach, impressions, follower growth).

    Args:
        period: Metrics period — 'day', 'week', or 'month'
    """
    if not INSTAGRAM_ACCOUNT_ID:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID not set in .env"})
    metrics = "reach,impressions,profile_views,follower_count"
    data = _ig_request(
        "get",
        f"{INSTAGRAM_ACCOUNT_ID}/insights",
        params={"metric": metrics, "period": period}
    )
    return json.dumps(data, indent=2)


@beta_tool
def create_post(image_url: str, caption: str) -> str:
    """Publish a photo post to Instagram immediately.

    The image must be at a publicly accessible URL. For local files, upload to a
    public host (Cloudinary, S3, etc.) first and provide the URL here.

    Args:
        image_url: Publicly accessible URL of the image
        caption: Post caption with hashtags
    """
    if not INSTAGRAM_ACCOUNT_ID:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID not set in .env"})
    # Step 1: Create media container
    container = _ig_request(
        "post",
        f"{INSTAGRAM_ACCOUNT_ID}/media",
        params={"image_url": image_url, "caption": caption}
    )
    if "error" in container or "id" not in container:
        return json.dumps({"error": "Failed to create media container", "details": container})
    creation_id = container["id"]
    # Step 2: Publish
    result = _ig_request(
        "post",
        f"{INSTAGRAM_ACCOUNT_ID}/media_publish",
        params={"creation_id": creation_id}
    )
    return json.dumps(result, indent=2)


@beta_tool
def create_reel(video_url: str, caption: str, cover_url: str = "") -> str:
    """Publish a Reel to Instagram.

    Args:
        video_url: Publicly accessible URL of the video (MP4, max 15 min)
        caption: Reel caption with hashtags
        cover_url: Optional cover image URL
    """
    if not INSTAGRAM_ACCOUNT_ID:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID not set in .env"})
    params: dict = {"media_type": "REELS", "video_url": video_url, "caption": caption}
    if cover_url:
        params["cover_url"] = cover_url
    container = _ig_request("post", f"{INSTAGRAM_ACCOUNT_ID}/media", params=params)
    if "error" in container or "id" not in container:
        return json.dumps({"error": "Failed to create Reel container", "details": container})
    result = _ig_request(
        "post",
        f"{INSTAGRAM_ACCOUNT_ID}/media_publish",
        params={"creation_id": container["id"]}
    )
    return json.dumps(result, indent=2)


@beta_tool
def draft_caption(
    post_type: str,
    book_title: str,
    key_message: str,
    tone: str = "warm and conversational",
    include_hashtags: bool = True,
) -> str:
    """Draft an Instagram caption (does NOT post — use create_post to publish).

    This tool calls Claude internally to draft the caption and returns it for review.

    Args:
        post_type: Type of post — 'quote', 'cover_reveal', 'chapter_tease',
                   'launch', 'behind_scenes', 'review_share', 'poll', 'general'
        book_title: The book this post is about
        key_message: Main point or content to convey
        tone: Writing tone e.g. 'warm and conversational', 'mysterious', 'exciting'
        include_hashtags: Whether to include relevant hashtags
    """
    hashtag_note = "Include 15-20 targeted hashtags for authors and readers." if include_hashtags else ""
    prompt = (
        f"Write an Instagram caption for an author post.\n"
        f"Post type: {post_type}\n"
        f"Book: {book_title}\n"
        f"Key message: {key_message}\n"
        f"Tone: {tone}\n"
        f"{hashtag_note}\n\n"
        f"Rules: hook in first line, CTA at end, emojis used tastefully."
    )
    draft_client = anthropic.Anthropic()
    response = draft_client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    caption = next((b.text for b in response.content if b.type == "text"), "")
    return json.dumps({"caption": caption, "character_count": len(caption)})


@beta_tool
def save_content_calendar(month_year: str, calendar: str) -> str:
    """Save a monthly Instagram content calendar to disk.

    Args:
        month_year: e.g. 'January 2025'
        calendar: Full content calendar in markdown table format
    """
    filename = re.sub(r"[^\w\-]", "_", month_year.lower()) + "_instagram_calendar.md"
    path = os.path.join(COVERS_DIR, filename)  # reuse covers dir for marketing assets
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Instagram Content Calendar: {month_year}\n\n{calendar}")
    return json.dumps({"saved": path})


def run(task: str) -> str:
    """Run the Instagram agent on a given task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[
            get_account_info, get_recent_posts, get_insights,
            draft_caption, create_post, create_reel, save_content_calendar,
        ],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from Instagram agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Instagram task completed."
