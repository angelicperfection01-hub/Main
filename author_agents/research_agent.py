"""Research agent — gathers information on topics using web search and saves findings."""
import os
import re
import json
import anthropic
from anthropic import beta_tool
from author_config import MODEL, MAX_TOKENS, RESEARCH_DIR

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert research assistant for authors. You gather accurate,
detailed information on any topic to support book writing. Your research is thorough,
well-organized, and cites sources clearly.

When asked to research a topic:
1. Search multiple angles: background, history, key facts, current trends, expert opinions
2. Note credible sources with URLs
3. Highlight the most compelling or surprising facts an author could use
4. Save your findings in a structured format using save_research

Always save your research before finishing so other agents can use it."""

# Server-side tool definitions
_WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search"}
_WEB_FETCH = {"type": "web_fetch_20260209", "name": "web_fetch"}


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:80]


@beta_tool
def save_research(topic: str, content: str) -> str:
    """Save research findings to disk for use by other agents.

    Args:
        topic: Short name/slug for the research topic (used as filename)
        content: Full research content in markdown format
    """
    filename = _safe_filename(topic) + ".md"
    path = os.path.join(RESEARCH_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Research: {topic}\n\n{content}")
    return json.dumps({"saved": path, "topic": topic, "bytes": len(content)})


@beta_tool
def list_research() -> str:
    """List all saved research files."""
    files = sorted(os.listdir(RESEARCH_DIR))
    md_files = [f for f in files if f.endswith(".md")]
    return json.dumps({"research_files": md_files, "count": len(md_files)})


@beta_tool
def read_research(topic: str) -> str:
    """Read saved research for a topic.

    Args:
        topic: Topic name or filename (with or without .md extension)
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


def run(task: str) -> str:
    """Run the research agent on a given task and return its final response."""
    runner = _client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[_WEB_SEARCH, _WEB_FETCH, save_research, list_research, read_research],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task}],
    )
    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        return "No response from research agent."
    text_blocks = [b.text for b in last_message.content if b.type == "text"]
    return "\n".join(text_blocks) if text_blocks else "Research completed."
