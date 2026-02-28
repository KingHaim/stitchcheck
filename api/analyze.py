# Vercel serverless: /api/analyze -> FastAPI backend (path "/" is rewritten to "/api/analyze")
from __future__ import annotations
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
from api._vercel_app import wrap_app
from backend.main import app as _app
app = wrap_app(_app, "/api/analyze")
