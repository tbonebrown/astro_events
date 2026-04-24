from __future__ import annotations

import importlib

from astro_api.config import AppSettings


settings = AppSettings()
service_main = importlib.import_module("services.api.main")
service_main = importlib.reload(service_main)
create_app = service_main.create_app
app = create_app(settings=settings)
