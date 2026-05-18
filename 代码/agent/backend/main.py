from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.services.vision import check_connection

print("Starting campus assistant...")
print("Checking model connection...")

# 启动时验证模型连接
try:
    if check_connection():
        print("Model connection OK")
    else:
        print("Model connection failed, but continuing to start (health check available)")
except Exception as e:
    print(f"Model connection check error: {e}")

app = FastAPI(title="校园学习助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# 挂载前端静态文件
import os
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")