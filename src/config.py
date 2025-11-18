import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
PARSER_PROMPT_PATH = PROJECT_ROOT / "src" / "parser" / "prompt.txt"
DATA_DIR = PROJECT_ROOT / "src" / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Data files
NOTES_FILE = DATA_DIR / "notes.json"
CALENDAR_FILE = DATA_DIR / "calendar.json"

# Logging
LOG_FILE = LOGS_DIR / "assistant.log"
LOG_LEVEL = "INFO"
