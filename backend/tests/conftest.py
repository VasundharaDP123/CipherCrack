"""Put the backend package root on sys.path so tests import like the app does."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
