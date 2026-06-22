import os
from dotenv import load_dotenv

load_dotenv()

STEPFUN_API_KEY = os.getenv("STEPFUN_API_KEY", "")
STEPFUN_BASE_URL = os.getenv("STEPFUN_BASE_URL", "https://api.stepfun.com/step_plan/v1")
ASR_BASE_URL = os.getenv("ASR_BASE_URL", "https://api.stepfun.com/v1")

# Video limits
MAX_VIDEO_SIZE_MB = 128
MAX_VIDEO_DURATION_MINUTES = 5

# Upload settings
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB for raw uploads

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "analyses.db")
