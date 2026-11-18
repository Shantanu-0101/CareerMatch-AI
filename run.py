"""Start the development server:  python run.py"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=debug)
