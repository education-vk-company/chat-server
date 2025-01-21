import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from api.routers import auth, chats, messages, realtime, users
from api.services.auth import AuthError
from api.services.chats import ChatError
from api.services.users import UserError

app = FastAPI(
    title="Messenger API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(messages.router, prefix="/api/chats", tags=["messages"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["realtime"])


@app.exception_handler(ChatError)
async def chat_error_handler(request: Request, exc: ChatError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.code})


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.code})


@app.exception_handler(UserError)
async def user_error_handler(request: Request, exc: UserError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.code})


@app.get("/api/health")
async def health():
    return {"status": "ok"}
