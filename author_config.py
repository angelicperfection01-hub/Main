import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Instagram / Meta Graph API
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")   # numeric IG Business Account ID

# WordPress (author website)
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "")                  # e.g. https://yoursite.com
WORDPRESS_USER = os.getenv("WORDPRESS_USER", "")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD", "") # WP Application Password

# Amazon KDP (no public API — used for metadata / manuscript prep)
KDP_EMAIL = os.getenv("KDP_EMAIL", "")
AUTHOR_PEN_NAME = os.getenv("AUTHOR_PEN_NAME", "")

MODEL = "claude-opus-4-6"
MAX_TOKENS = 16000

# Local storage paths
DATA_DIR = os.getenv("AUTHOR_DATA_DIR", "./author_data")
RESEARCH_DIR = os.path.join(DATA_DIR, "research")
OUTLINES_DIR = os.path.join(DATA_DIR, "outlines")
MANUSCRIPTS_DIR = os.path.join(DATA_DIR, "manuscripts")
COVERS_DIR = os.path.join(DATA_DIR, "covers")
WEBSITE_DIR = os.path.join(DATA_DIR, "website")

# Ensure all dirs exist
for _d in (RESEARCH_DIR, OUTLINES_DIR, MANUSCRIPTS_DIR, COVERS_DIR, WEBSITE_DIR):
    os.makedirs(_d, exist_ok=True)
