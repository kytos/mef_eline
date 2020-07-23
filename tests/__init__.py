"""NApp Tests."""
import os
import sys
from pathlib import Path

BASE_ENV = Path(os.environ.get('VIRTUAL_ENV', '/'))
NAPPS_DIR = BASE_ENV / 'var/lib/kytos/'
sys.path.insert(0, str(NAPPS_DIR))
