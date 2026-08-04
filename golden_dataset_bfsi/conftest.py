"""Make ``golden_bfsi`` importable when pytest runs from this directory."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
