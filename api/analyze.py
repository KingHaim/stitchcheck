# Vercel serverless: /api/analyze -> FastAPI backend
from __future__ import annotations
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from backend.main import app
