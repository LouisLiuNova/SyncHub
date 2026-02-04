import os
import shutil
import random
from datetime import datetime
from typing import List, Optional

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
    Body,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import func
from jose import jwt, JWTError
from . import models, database, auth

# --- 配置 ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="SyncHub")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# --- WebSocket Manager (保持不变) ---
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
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)


manager = ConnectionManager()

# --- 辅助函数：颜色生成 ---
COLORS = [
    ("bg-red-100", "text-red-700"),
    ("bg-orange-100", "text-orange-700"),
    ("bg-amber-100", "text-amber-700"),
    ("bg-green-100", "text-green-700"),
    ("bg-emerald-100", "text-emerald-700"),
    ("bg-teal-100", "text-teal-700"),
    ("bg-cyan-100", "text-cyan-700"),
    ("bg-sky-100", "text-sky-700"),
    ("bg-blue-100", "text-blue-700"),
    ("bg-indigo-100", "text-indigo-700"),
    ("bg-violet-100", "text-violet-700"),
    ("bg-purple-100", "text-purple-700"),
    ("bg-fuchsia-100", "text-fuchsia-700"),
    ("bg-pink-100", "text-pink-700"),
    ("bg-rose-100", "text-rose-700"),
]


def get_random_color():
    return random.choice(COLORS)


# --- Pydantic Models ---
class TagCreate(BaseModel):
    name: str


# --- API 路由 ---


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    user = (
        db.query(models.User).filter(models.User.username == form_data.username).first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
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
    hashed_pw = auth.get_password_hash(password)
    new_user = models.User(username=username, hashed_password=hashed_pw)
    db.add(new_user)

    # 创建默认标签
    if db.query(models.Tag).count() == 0:
        default_tags = ["General", "Code", "Work", "Personal"]
        for t_name in default_tags:
            bg, txt = get_random_color()
            db.add(models.Tag(name=t_name, color_bg=bg, color_text=txt))

    db.commit()
    return {"message": "User created"}


# --- 标签 API ---
@app.get("/api/tags")
async def get_tags(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Tag).all()


@app.post("/api/tags")
async def create_tag(
    tag: TagCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # --- 修改：使用 func.lower 进行大小写不敏感查重 ---
    if (
        db.query(models.Tag)
        .filter(func.lower(models.Tag.name) == tag.name.lower())
        .first()
    ):
        raise HTTPException(status_code=400, detail="Tag already exists")

    bg, txt = get_random_color()
    # 存入数据库时保留用户输入的大小写格式，或者你可以强制 tag.name.upper()
    # 这里我们保留原样，通过前端 CSS 控制显示为大写
    new_tag = models.Tag(name=tag.name, color_bg=bg, color_text=txt)
    db.add(new_tag)
    db.commit()
    await manager.broadcast("update:tags")
    return new_tag


@app.delete("/api/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if tag:
        # --- fix: 禁止删除 General 标签 ---
        if tag.name == "General":
            raise HTTPException(status_code=400, detail="Cannot delete default tag")
        # -----------------------------------
        db.delete(tag)
        db.commit()
        await manager.broadcast("update:tags")
    return {"message": "Deleted"}


# --- 剪贴板 API ---
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


# --- 文件 API ---
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
            "tag": f.tag,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
            "user": f.owner.username,
        }
        for f in files
    ]


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    tag: str = Form("General"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    safe_filename = f"{datetime.now().timestamp()}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    file_size = os.path.getsize(file_location)
    # 存入 tag
    db_file = models.FileItem(
        filename=file.filename,
        filepath=file_location,
        filesize=file_size,
        tag=tag,
        user_id=current_user.id,
    )
    db.add(db_file)
    db.commit()
    await manager.broadcast("update:files")
    return {"message": "Uploaded"}


@app.get("/api/download/{file_id}")
async def download_file(
    file_id: int,
    token: str,  # 1. 接收 URL 中的 token 参数
    db: Session = Depends(database.get_db),
):
    # 2. 手动验证 Token
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise HTTPException(status_code=401, detail="Invalid token")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 3. 验证通过，查找文件
    file_item = db.query(models.FileItem).filter(models.FileItem.id == file_id).first()
    if not file_item or not os.path.exists(file_item.filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_item.filepath, filename=file_item.filename)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
