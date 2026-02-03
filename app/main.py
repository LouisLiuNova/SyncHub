import os
import shutil
from datetime import datetime
from typing import List

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from starlette.requests import Request
from sqlalchemy.orm import Session

# 引入我们拆分出来的模块
from . import models, database, auth

# --- 配置 ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# 初始化数据库表
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="SyncHub", description="跨设备剪贴板与文件共享")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# --- WebSocket 管理器 ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # 复制列表进行迭代，防止迭代时修改列表报错
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)


manager = ConnectionManager()

# --- API 路由 ---


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    # 使用 auth 模块验证
    user = (
        db.query(models.User).filter(models.User.username == form_data.username).first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # 使用 auth 模块生成 token
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db),
):
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    # 使用 auth 模块哈希密码
    hashed_pw = auth.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}


# 剪贴板 API
@app.get("/api/clipboard")
async def get_clipboard(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    items = (
        db.query(models.ClipboardItem)
        .order_by(models.ClipboardItem.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": i.id,
            "content": i.content,
            "tag": i.tag,
            "created_at": i.created_at.strftime("%Y-%m-%d %H:%M"),
            "user": i.owner.username,
        }
        for i in items
    ]


@app.post("/api/clipboard")
async def add_clipboard(
    content: str = Form(...),
    tag: str = Form("General"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    item = models.ClipboardItem(content=content, tag=tag, user_id=current_user.id)
    db.add(item)
    db.commit()
    await manager.broadcast("update:clipboard")
    return {"message": "Added"}


# 文件 API
@app.get("/api/files")
async def get_files(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    files = (
        db.query(models.FileItem)
        .order_by(models.FileItem.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "size": f"{f.filesize/1024:.1f} KB",
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
            "user": f.owner.username,
        }
        for f in files
    ]


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # 使用时间戳防止文件名冲突
    safe_filename = f"{datetime.now().timestamp()}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    file_size = os.path.getsize(file_location)
    db_file = models.FileItem(
        filename=file.filename,
        filepath=file_location,
        filesize=file_size,
        user_id=current_user.id,
    )
    db.add(db_file)
    db.commit()
    await manager.broadcast("update:files")
    return {"message": "Uploaded"}


@app.get("/api/download/{file_id}")
async def download_file(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    file_item = db.query(models.FileItem).filter(models.FileItem.id == file_id).first()
    if not file_item or not os.path.exists(file_item.filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_item.filepath, filename=file_item.filename)


# WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
