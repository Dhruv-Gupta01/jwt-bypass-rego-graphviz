from flask import Flask

from .middleware import JWTMiddleware
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    app.wsgi_app = JWTMiddleware(app.wsgi_app)
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
