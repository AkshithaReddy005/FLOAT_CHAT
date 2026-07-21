from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from database.database import create_tables
from routers import deps
from routers.admin import router as admin_router
from routers.chat import router as chat_router
from routers.researcher import router as researcher_router
from routers.system import router as system_router

load_dotenv()

app = FastAPI(title="FloatChat ARGO Data System")

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "localhost")
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5432")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{FRONTEND_HOST}:{FRONTEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        f"http://{BACKEND_HOST}:{BACKEND_PORT}",
        f"http://127.0.0.1:{BACKEND_PORT}"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    create_tables()
    deps.initialize()

@app.get("/")
def read_root():
    return {"message": "FloatChat ARGO Data System API"}

app.include_router(admin_router, prefix="/admin")
app.include_router(chat_router)
app.include_router(researcher_router, prefix="/researcher")
app.include_router(system_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)