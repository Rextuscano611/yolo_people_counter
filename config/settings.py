import os
from dotenv import load_dotenv

load_dotenv()

# Device & model
DEVICE = os.getenv("DEVICE", "cpu")
MODEL_NAME = os.getenv("MODEL", "yolo11n.pt")
MODEL_PATH = os.path.join("models", MODEL_NAME)

# Source
SOURCE = os.getenv("SOURCE", "data/videos/test.mp4")

# Detection
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
PERSON_CLASS_ID = 0

# Staff filter
GREEN_LOWER = (35, 50, 50)   # HSV
GREEN_UPPER = (85, 255, 255) # HSV
GREEN_THRESHOLD = float(os.getenv("GREEN_THRESHOLD", "0.25"))

# Database
DB_PATH = os.getenv("DB_PATH", "data/db/footfall.db")

# Display
SHOW_VIDEO = True