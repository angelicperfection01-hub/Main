"""Author Network Orchestrator — routes tasks to the right specialist agents."""
import anthropic
from anthropic import beta_tool
from author_config import MODEL, MAX_TOKENS

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are the AI chief of staff for a self-publishing author. You
coordinate a network of specialist agents to help the author research, write, edit,
design, publish, and promote their books.

Your specialist agents:

1. **Research Agent** — searches the web for any topic, saves findings for other agents
2. **Outline Agent** — creates detailed book outlines from research; plans chapter structure
3. **Writer Agent** — drafts full book chapters based on outlines, tracks word count
4. **Editor Agent** — proofreads and line-edits chapters, saves polished versions
5. **Cover Designer Agent** — creates cover briefs, Midjourney/DALL-E prompts, back cover copy
6. **KDP Agent** — prepares Amazon KDP upload packages: metadata, keywords, categories, pricing
7. **Instagram Agent** — manages the author's Instagram: posts, Reels, insights, content calendars
8. **Website Agent** — manages the WordPress author website: blog posts, pages, SEO

Workflow intelligence:
- New book project → Research → Outline → Write → Edit → Cover → KDP
- Launch campaign → Cover brief + KDP package + Instagram calendar + website blog post
- Single task → Route directly to the most relevant agent
- Complex tasks → Chain multiple agents in the right order

Always tell the author which agents you're calling and why. After completing multi-agent
tasks, give a clear summary of everything accomplished."""


@beta_tool
def run_research_agent(task: str) -> str:
    """Delegate to the research agent to search the web and save findings.

    Args:
        task: Research task description — topic, scope, and what to focus on
    """
    from author_agents.research_agent import run
    return run(task)


@beta_tool
def run_outline_agent(task: str) -> str:
    """Delegate to the outline agent to create a book structure.

    Args:
        task: Outline task — book title, genre, target audience, any constraints
    """
    from author_agents.outline_agent import run
    return run(task)


@beta_tool
def run_writer_agent(task: str) -> str:
    """Delegate to the writer agent to draft book content.

    Args:
        task: Writing task — book title, chapter(s) to write, tone, word count target
    """
    from author_agents.writer_agent import run
    return run(task)


@beta_tool
def run_editor_agent(task: str) -> str:
    """Delegate to the editor agent to review and polish chapters.

    Args:
        task: Editing task — book title, chapter(s) to edit, type of edit needed
    """
    from author_agents.editor_agent import run
    return run(task)


@beta_tool
def run_cover_designer_agent(task: str) -> str:
    """Delegate to the cover designer agent to create cover briefs and image prompts.

    Args:
        task: Cover design task — book title, genre, mood, any specific requests
    """
    from author_agents.cover_designer_agent import run
    return run(task)


@beta_tool
def run_kdp_agent(task: str) -> str:
    """Delegate to the KDP agent to prepare Amazon publishing packages.

    Args:
        task: KDP task — book title, publishing goals, pricing preferences
    """
    from author_agents.kdp_agent import run
    return run(task)


@beta_tool
def run_instagram_agent(task: str) -> str:
    """Delegate to the Instagram agent to manage social media.

    Args:
        task: Instagram task — content type, book to promote, post goal
    """
    from author_agents.instagram_agent import run
    return run(task)


@beta_tool
def run_website_agent(task: str) -> str:
    """Delegate to the website agent to manage the author's WordPress site.

    Args:
        task: Website task — content type, subject, publish status
    """
    from author_agents.website_agent import run
    return run(task)


def run(task: str) -> str:
    """Run the orchestrator on a high-level author task."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[
            run_research_agent,
            run_outline_agent,
            run_writer_agent,
            run_editor_agent,
            run_cover_designer_agent,
            run_kdp_agent,
            run_instagram_agent,
            run_website_agent,
        ],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from orchestrator."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Task completed."
