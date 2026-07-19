from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "raw"
MODEL_PATH = PROJECT_ROOT / "models"
MODEL_DIR = PROJECT_ROOT / "models"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "cloudcostai.db"
