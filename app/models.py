from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class ClipboardItem(Base):
    __tablename__ = "clipboard_items"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    tag = Column(String, default="General")
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")


class FileItem(Base):
    __tablename__ = "file_items"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    filepath = Column(String)
    filesize = Column(Integer)  # in bytes
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")
