import sys
import os

# backend/ 모듈을 Python path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app  # noqa: F401, E402 — Vercel ASGI entry point
