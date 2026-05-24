from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from services.editor_agent.api.routes.documents import router as documents_router
from services.editor_agent.api.routes.health import router as health_router
from services.editor_agent.api.routes.templates import router as templates_router

app = FastAPI(title="Editor Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(templates_router)
app.include_router(documents_router)


if __name__ == "__main__":
    uvicorn.run("services.editor_agent.api.main:app", host="127.0.0.1", port=8003, reload=False)
