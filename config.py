import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ETSY_API_KEY = os.getenv("ETSY_API_KEY", "")
ETSY_ACCESS_TOKEN = os.getenv("ETSY_ACCESS_TOKEN", "")
ETSY_SHOP_ID = os.getenv("ETSY_SHOP_ID", "")

MODEL = "claude-opus-4-6"
MAX_TOKENS = 16000
ETSY_BASE_URL = "https://openapi.etsy.com/v3"
