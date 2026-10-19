# Vercel serverless entry: vercel.json rewrites every request here, and the
# Flask app routes it (pages, /static assets and /api JSON alike).
from portal import app  # noqa: F401
