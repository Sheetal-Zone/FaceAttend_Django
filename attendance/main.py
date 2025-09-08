from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from attendance.api.v1 import liveness

app = FastAPI(title="Face Attendance API")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(liveness.router, prefix="/api/v1/liveness", tags=["Liveness"])

@app.get("/")
def root():
    return {"message": "Face Attendance API is running"}


