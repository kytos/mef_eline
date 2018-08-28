"""Module to test the napp kytos/mef_eline."""
import sys
import os
from pathlib import Path

if 'VIRTUAL_ENV' in os.environ:
    BASE_ENV = Path(os.environ['VIRTUAL_ENV'])
else:
    BASE_ENV = Path('/')

MEF_ELINE_PATH = BASE_ENV / '/var/lib/kytos/napps/..'

sys.path.insert(0, str(MEF_ELINE_PATH))
