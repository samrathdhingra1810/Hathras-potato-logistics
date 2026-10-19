"""Local development server: python run.py -> http://localhost:5000"""
import os

from portal import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
