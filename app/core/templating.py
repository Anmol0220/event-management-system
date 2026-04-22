from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import get_settings


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

templates.env.globals["app_name"] = get_settings().app_name
templates.env.globals["current_year"] = lambda: datetime.now(timezone.utc).year
