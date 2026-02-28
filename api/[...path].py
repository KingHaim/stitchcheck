"""
Vercel serverless catch-all: run the FastAPI backend for all /api/* routes.
Request path is preserved, so /api/analyze, /api/analyze-text, /api/health work.
Set REPLICATE_API_TOKEN (and optional REPLICATE_MODEL) in Vercel project env vars.
"""
from __future__ import annotations
import sys
import os

# Project root so "from backend.main import app" and backend's imports work
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.main import app
