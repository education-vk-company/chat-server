from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.staticfiles import StaticFiles

from server.app import wsgi
from server.apps.participants.routers import router as participants_router
from server.config import settings

app = FastAPI()

app.mount(settings.WSGI_URL, WSGIMiddleware(app=wsgi.application))
app.mount(settings.STATIC_URL, StaticFiles(directory=settings.STATIC_ROOT))

app.include_router(participants_router)
