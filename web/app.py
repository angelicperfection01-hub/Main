"""
Author Agent Network — Flask web app.
Run:  python web/app.py
Then open http://localhost:5000
"""
import importlib
import json
import os
import sys
import threading
import queue

from flask import Flask, render_template, request, Response, jsonify, stream_with_context

# ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

app = Flask(__name__)

AGENTS = {
    "orchestrator":  {"module": "author_agents.orchestrator",          "label": "Orchestrator",     "icon": "🎯", "desc": "Routes tasks to the right specialists"},
    "research":      {"module": "author_agents.research_agent",        "label": "Research",         "icon": "🔍", "desc": "Web search & saves findings"},
    "outline":       {"module": "author_agents.outline_agent",         "label": "Outline",          "icon": "📋", "desc": "Structures your book chapter by chapter"},
    "writer":        {"module": "author_agents.writer_agent",          "label": "Writer",           "icon": "✍️",  "desc": "Drafts full chapters"},
    "editor":        {"module": "author_agents.editor_agent",          "label": "Editor",           "icon": "📝", "desc": "Polishes & proofreads your manuscript"},
    "cover":         {"module": "author_agents.cover_designer_agent",  "label": "Cover Designer",   "icon": "🎨", "desc": "Cover briefs & AI image prompts"},
    "kdp":           {"module": "author_agents.kdp_agent",             "label": "KDP Publishing",   "icon": "📚", "desc": "Amazon KDP upload packages"},
    "instagram":     {"module": "author_agents.instagram_agent",       "label": "Instagram",        "icon": "📸", "desc": "Social media content & posting"},
    "website":       {"module": "author_agents.website_agent",         "label": "Website",          "icon": "🌐", "desc": "WordPress blog posts & pages"},
}

DATA_DIRS = {
    "Research":    "./author_data/research",
    "Outlines":    "./author_data/outlines",
    "Manuscripts": "./author_data/manuscripts",
    "Covers":      "./author_data/covers",
    "Website":     "./author_data/website",
}


def _run_agent_streamed(agent_key: str, task: str, result_queue: queue.Queue) -> None:
    """Run an agent in a thread, put its result into the queue."""
    try:
        cfg = AGENTS[agent_key]
        mod = importlib.import_module(cfg["module"])
        result = mod.run(task)
        result_queue.put(("done", result))
    except Exception as exc:
        result_queue.put(("error", str(exc)))


@app.route("/")
def index():
    return render_template("index.html", agents=AGENTS)


@app.route("/files")
def files():
    """Return JSON list of files in each data directory."""
    tree = {}
    for label, path in DATA_DIRS.items():
        abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
        if not os.path.exists(abs_path):
            tree[label] = []
            continue
        entries = []
        for root, dirs, filenames in os.walk(abs_path):
            dirs.sort()
            rel_root = os.path.relpath(root, abs_path)
            for fname in sorted(filenames):
                rel = os.path.join(rel_root, fname) if rel_root != "." else fname
                entries.append(rel)
        tree[label] = entries
    return jsonify(tree)


@app.route("/file")
def file_content():
    """Return the contents of a file in author_data."""
    category = request.args.get("category", "")
    filename = request.args.get("name", "")
    if not category or not filename:
        return jsonify({"error": "Missing category or name"}), 400
    base = DATA_DIRS.get(category)
    if not base:
        return jsonify({"error": "Unknown category"}), 400
    project_root = os.path.dirname(os.path.dirname(__file__))
    abs_path = os.path.realpath(os.path.join(project_root, base, filename))
    allowed_root = os.path.realpath(os.path.join(project_root, base))
    # Security: prevent path traversal
    if not abs_path.startswith(allowed_root + os.sep) and abs_path != allowed_root:
        return jsonify({"error": "Access denied"}), 403
    if not os.path.isfile(abs_path):
        return jsonify({"error": "File not found"}), 404
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return jsonify({"content": content, "filename": filename})


@app.route("/chat", methods=["POST"])
def chat():
    """Run an agent and stream the result back as SSE."""
    data = request.get_json(force=True)
    agent_key = data.get("agent", "orchestrator")
    task = data.get("task", "").strip()

    if not task:
        return jsonify({"error": "No task provided"}), 400
    if agent_key not in AGENTS:
        return jsonify({"error": "Unknown agent"}), 400

    result_queue: queue.Queue = queue.Queue()
    thread = threading.Thread(
        target=_run_agent_streamed,
        args=(agent_key, task, result_queue),
        daemon=True,
    )
    thread.start()

    def generate():
        # Send a heartbeat while waiting
        while thread.is_alive():
            try:
                status, payload = result_queue.get(timeout=1.0)
                yield f"data: {json.dumps({'type': status, 'text': payload})}\n\n"
                return
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        # Drain queue after thread ends
        try:
            status, payload = result_queue.get_nowait()
            yield f"data: {json.dumps({'type': status, 'text': payload})}\n\n"
        except queue.Empty:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Agent returned no response'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, threaded=True)
