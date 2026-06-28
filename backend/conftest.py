"""Ensure the backend root is importable as the `app` package during tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
