"""CipherCrack backend: Flask REST API plus Socket.IO solver streaming.

    python app.py

Flask rather than Django purely for Flask-SocketIO: the Crack Live page needs
to push a progress frame every hundred iterations, and this is the shortest
path from a background thread to the browser.
"""

import argparse
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

import db
from api import api, register_sockets

# Origins the browser may connect from: the Vite dev server (5173), Vite's
# preview server (4173), and the backend's own port for anyone who opens the API
# directly.  Both spellings of loopback are listed because a browser treats
# localhost and 127.0.0.1 as different origins, and a mismatch here shows up as
# a silently dead Socket.IO connection rather than a useful error.
ALLOWED_ORIGINS = "*"

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["JSON_SORT_KEYS"] = False
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    app.register_blueprint(api)
    db.init()

    @app.get("/")
    def index():
        return jsonify({
            "name": "CipherCrack",
            "docs": "/api/health",
            "socket_events": ["start_crack", "stop_crack"],
        })

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": str(error)}), 500

    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")
    register_sockets(socketio)
    return app


def warm_up():
    """Load the models once at boot so the first request is not slow."""
    from ml.language_model import get_model
    get_model()
    try:
        from ml.identifier import get_identifier
        get_identifier()
        print("  identifier   : loaded")
    except FileNotFoundError:
        print("  identifier   : NOT TRAINED -> python -m scripts.train_identifier")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app()
    print("CipherCrack backend")
    print("  language model: loaded")
    warm_up()
    print(f"  listening    : http://{args.host}:{args.port}")
    socketio.run(app, host=args.host, port=args.port, debug=args.debug,
                 allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
