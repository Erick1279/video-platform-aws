import hashlib
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from database import init_db, get_session
from models import (
    User, UserCreate, UserRead,
    Video, VideoRead,
    Comment, CommentBase, CommentRead
)
from s3 import upload_file_to_s3

app = FastAPI(
    title="Video Platform API",
    description="API para plataforma de videos desplegada en AWS EC2, RDS y S3",
    version="1.0.0"
)

# Habilitar CORS para que React en S3 pueda comunicarse con la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

@app.on_event("startup")
def on_startup():
    init_db()

# ==================== USUARIOS ====================

@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
def create_user(user_in: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado")
    
    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password)
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/login", tags=["Usuarios"])
def login(email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or user.password_hash != hash_password(password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return {"message": "Login exitoso", "user_id": user.id, "name": user.name, "email": user.email}

@app.get("/users/{user_id}", response_model=UserRead, tags=["Usuarios"])
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# ==================== VIDEOS ====================

@app.post("/videos", response_model=VideoRead, status_code=status.HTTP_201_CREATED, tags=["Videos"])
async def create_video(
    title: str = Form(...),
    description: str = Form(...),
    user_id: int = Form(...),
    video_file: UploadFile = File(...),
    thumbnail_file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    video_bytes = await video_file.read()
    thumb_bytes = await thumbnail_file.read()

    video_url = upload_file_to_s3(video_bytes, video_file.filename, video_file.content_type, is_video=True)
    thumb_url = upload_file_to_s3(thumb_bytes, thumbnail_file.filename, thumbnail_file.content_type, is_video=False)

    video = Video(
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumb_url,
        user_id=user_id,
        views=0
    )
    session.add(video)
    session.commit()
    session.refresh(video)

    return VideoRead(
        id=video.id,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        views=video.views,
        user_id=video.user_id,
        created_at=video.created_at,
        user_name=user.name
    )

@app.get("/videos", response_model=List[VideoRead], tags=["Videos"])
def list_videos(user_id: Optional[int] = None, session: Session = Depends(get_session)):
    query = select(Video)
    if user_id:
        query = query.where(Video.user_id == user_id)
    
    videos = session.exec(query.order_by(Video.created_at.desc())).all()
    results = []
    for v in videos:
        u = session.get(User, v.user_id)
        results.append(VideoRead(
            id=v.id,
            title=v.title,
            description=v.description,
            video_url=v.video_url,
            thumbnail_url=v.thumbnail_url,
            views=v.views,
            user_id=v.user_id,
            created_at=v.created_at,
            user_name=u.name if u else "Anónimo"
        ))
    return results

@app.get("/videos/{video_id}", response_model=VideoRead, tags=["Videos"])
def get_video(video_id: int, session: Session = Depends(get_session)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Incrementar vistas
    video.views += 1
    session.add(video)
    session.commit()
    session.refresh(video)
    
    user = session.get(User, video.user_id)
    return VideoRead(
        id=video.id,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        views=video.views,
        user_id=video.user_id,
        created_at=video.created_at,
        user_name=user.name if user else "Anónimo"
    )

@app.put("/videos/{video_id}", response_model=VideoRead, tags=["Videos"])
def update_video(
    video_id: int,
    title: str = Form(...),
    description: str = Form(...),
    session: Session = Depends(get_session)
):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    video.title = title
    video.description = description
    session.add(video)
    session.commit()
    session.refresh(video)
    
    user = session.get(User, video.user_id)
    return VideoRead(
        id=video.id,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        views=video.views,
        user_id=video.user_id,
        created_at=video.created_at,
        user_name=user.name if user else "Anónimo"
    )

@app.delete("/videos/{video_id}", tags=["Videos"])
def delete_video(video_id: int, session: Session = Depends(get_session)):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Eliminar comentarios asociados
    comments = session.exec(select(Comment).where(Comment.video_id == video_id)).all()
    for c in comments:
        session.delete(c)
        
    session.delete(video)
    session.commit()
    return {"message": "Video eliminado correctamente"}

# ==================== COMENTARIOS ====================

@app.post("/videos/{video_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED, tags=["Comentarios"])
def add_comment(
    video_id: int,
    user_id: int = Form(...),
    content: str = Form(...),
    session: Session = Depends(get_session)
):
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    comment = Comment(content=content, user_id=user_id, video_id=video_id)
    session.add(comment)
    session.commit()
    session.refresh(comment)

    return CommentRead(
        id=comment.id,
        content=comment.content,
        user_id=comment.user_id,
        video_id=comment.video_id,
        created_at=comment.created_at,
        user_name=user.name
    )

@app.get("/videos/{video_id}/comments", response_model=List[CommentRead], tags=["Comentarios"])
def list_comments(video_id: int, session: Session = Depends(get_session)):
    comments = session.exec(select(Comment).where(Comment.video_id == video_id).order_by(Comment.created_at.desc())).all()
    results = []
    for c in comments:
        u = session.get(User, c.user_id)
        results.append(CommentRead(
            id=c.id,
            content=c.content,
            user_id=c.user_id,
            video_id=c.video_id,
            created_at=c.created_at,
            user_name=u.name if u else "Anónimo"
        ))
    return results
