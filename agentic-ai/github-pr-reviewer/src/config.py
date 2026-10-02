import os
from pathlib import Path

from dotenv import load_dotenv


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DEFAULT_OWNER = os.getenv("GITHUB_OWNER", "").strip()
DEFAULT_REPO = os.getenv("GITHUB_REPO", "").strip()


# LLM configuration
EXTRACTION_MODEL = "openai/gpt-oss-20b"
REVIEW_MODEL = "openai/gpt-oss-120b"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Review configuration
DELAY_SECONDS = 2
MAX_CHARS = int(os.getenv("MAX_REVIEW_CHARS", "4500"))

# File paths
CODE_STANDARDS_PATH = PROJECT_ROOT / "CODE_STANDARDS.md"


# Validate required configuration
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is missing from .env")
