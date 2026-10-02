from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class UserBase(SQLModel):
    name: str
    email: str

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    videos: List["Video"] = Relationship(back_populates="user")
    comments: List["Comment"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    created_at: datetime

class VideoBase(SQLModel):
    title: str
    description: str

class Video(VideoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_url: str
    thumbnail_url: str
    views: int = Field(default=0)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship(back_populates="videos")
    comments: List["Comment"] = Relationship(back_populates="video")

class VideoRead(VideoBase):
    id: int
    video_url: str
    thumbnail_url: str
    views: int
    user_id: int
    created_at: datetime
    user_name: Optional[str] = None

class CommentBase(SQLModel):
    content: str

class Comment(CommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    video_id: int = Field(foreign_key="video.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship(back_populates="comments")
    video: Optional[Video] = Relationship(back_populates="comments")

class CommentRead(CommentBase):
    id: int
    user_id: int
    video_id: int
    created_at: datetime
    user_name: Optional[str] = None
