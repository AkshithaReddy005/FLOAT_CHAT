from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from presentation.controllers.admin_controller import router as admin_router
from presentation.controllers.researcher_controller import router as researcher_router
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="FloatChat ARGO Data System")

# Get environment variables
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "localhost")
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5432")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://{FRONTEND_HOST}:{FRONTEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        "http://localhost:5173",  # Keep for backward compatibility during development
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(researcher_router)

@app.get("/")
def read_root():
    return {"message": "FloatChat ARGO Data System API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)