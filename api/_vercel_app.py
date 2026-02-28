"""
Wrap the FastAPI app so that when Vercel passes path "/" to a serverless function,
we rewrite it to the full path (e.g. /api/analyze) so the backend routes match.
"""
from __future__ import annotations


def wrap_app(app, path: str):
    """Return an ASGI app that rewrites scope['path'] from '/' to path before calling app."""
    async def wrapped(scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") == "/":
            scope = dict(scope, path=path)
        await app(scope, receive, send)
    return wrapped
