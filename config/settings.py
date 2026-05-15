import os
from dotenv import load_dotenv

load_dotenv()

# Device & model
DEVICE     = os.getenv("DEVICE", "cpu")
MODEL_NAME = os.getenv("MODEL",  "yolo11n.pt")
MODEL_PATH = os.path.join("models", MODEL_NAME)

# Source
SOURCE = os.getenv("SOURCE", "data/videos/test.mp4")

# Detection
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
PERSON_CLASS_ID      = 0

# Staff filter
GREEN_LOWER = (28, 33, 90)
GREEN_UPPER = (65, 147, 255)
GREEN_THRESHOLD = float(os.getenv("GREEN_THRESHOLD", "0.18"))

# Database
DB_PATH = os.getenv("DB_PATH", "data/db/footfall.db")

# Display
SHOW_VIDEO = os.environ.get("SHOW_WINDOW", "1") == "1"

# Tripwire LINE_Y — optional override.
# If set in .env (e.g. LINE_Y=240), the mouse-click selector is skipped.
# If absent or 0, main.py launches the interactive selector on first frame.
_line_y_raw = os.getenv("LINE_Y", "0")
LINE_Y = int(_line_y_raw) if _line_y_raw.strip().isdigit() and int(_line_y_raw) > 0 else None


# Add below DB_PATH
INVERT_CROSSING = os.getenv("INVERT_CROSSING", "false").lower() == "true"