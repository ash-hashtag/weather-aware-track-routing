"""Vercel Python entrypoint: serves the Django app in ./backend as a WSGI function.

vercel.json rewrites /api/* here; Django sees the original path, so its `api/` URLs match.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
