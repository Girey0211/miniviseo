import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Notion Configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_CALENDAR_DATABASE_ID = os.getenv("NOTION_CALENDAR_DATABASE_ID")  # Calendar database
NOTION_NOTES_DATABASE_ID = os.getenv("NOTION_NOTES_DATABASE_ID")  # Notes database

# Configuration validation
if NOTION_API_KEY and not NOTION_NOTES_DATABASE_ID:
    logger.warning("NOTION_API_KEY is set but NOTION_NOTES_DATABASE_ID is missing. Notion notes functionality will be disabled.")
if NOTION_API_KEY and not NOTION_CALENDAR_DATABASE_ID:
    logger.warning("NOTION_API_KEY is set but NOTION_CALENDAR_DATABASE_ID is missing. Notion calendar functionality will be disabled.")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
PARSER_PROMPT_PATH = PROJECT_ROOT / "src" / "parser" / "prompt.txt"
DATA_DIR = PROJECT_ROOT / "src" / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Data files
NOTES_FILE = DATA_DIR / "notes.json"

# Logging
LOG_FILE = LOGS_DIR / "assistant.log"
LOG_LEVEL = "INFO"
