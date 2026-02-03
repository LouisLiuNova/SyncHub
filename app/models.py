from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    color_bg = Column(String)  # Tailwind class, e.g., 'bg-red-100'
    color_text = Column(String)  # Tailwind class, e.g., 'text-red-700'


class ClipboardItem(Base):
    __tablename__ = "clipboard_items"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    tag = Column(String, default="General")  # 存储标签名称
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")


class FileItem(Base):
    __tablename__ = "file_items"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    filepath = Column(String)
    filesize = Column(Integer)
    tag = Column(String, default="General")  # 新增：存储标签名称
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")
