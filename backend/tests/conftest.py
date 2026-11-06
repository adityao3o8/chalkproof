import sys
from pathlib import Path

# Allow `from app...` when running pytest from backend/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
