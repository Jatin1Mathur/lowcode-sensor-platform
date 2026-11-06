"""Flask REST service that validates ESP32 sensor data and feeds Oracle APEX."""

import logging

from flask import Flask

from .config import Config
from .errors import register_error_handlers
from .repository import ApexRepository, InMemoryRepository
from .routes import api


def _build_repository(app: Flask):
    backend = app.config["STORAGE_BACKEND"]
    if backend == "memory":
        return InMemoryRepository()
    if backend == "apex":
        base_url = app.config["APEX_ORDS_BASE_URL"]
        if not base_url:
            raise RuntimeError("APEX_ORDS_BASE_URL must be set when STORAGE_BACKEND=apex")
        return ApexRepository(
            base_url,
            token=app.config["APEX_ORDS_TOKEN"],
            timeout=app.config["APEX_TIMEOUT_SECONDS"],
        )
    raise RuntimeError(f"Unknown STORAGE_BACKEND: {backend}")


def create_app(config: dict | None = None, repository=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app.extensions["sensor_repository"] = repository or _build_repository(app)
    register_error_handlers(app)
    app.register_blueprint(api)
    return app
