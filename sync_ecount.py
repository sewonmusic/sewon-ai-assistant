import logging
import sys
from src.ecount_mapping.sync import run_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    success = run_sync()
    sys.exit(0 if success else 1)
