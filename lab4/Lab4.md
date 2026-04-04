# Лабораторная работа 4.1. Создание и развертывание полнофункционального приложения

# Цель работы

Применить полученные знания по созданию и развертыванию трехзвенного приложения (Frontend + Backend + Database) в кластере Kubernetes. Научиться организовывать взаимодействие между микросервисами.

# Индивидуальное задание

| Вариант | Название системы | Бизнес-задача | Данные (Пример) |
|---------|------------------|---------------|-----------------|
| 12 | Rocket Launch Analytics | Мониторинг и анализ космических запусков | Название миссии, статус запуска, дата старта, провайдер, изображения ракет |

# Технический стек и окружение

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Операционная система** | Ubuntu | 22.04 LTS |
| **Контейнеризация** | Docker | |
| **Оркестрация** | Minikube (Driver: Docker), Kubernetes | |
| **База данных** | PostgreSQL | 15-alpine |
| **Язык программирования** | Python | 3.11 |
| **Backend** | FastAPI, Uvicorn | 0.104.1 |
| **Frontend** | Streamlit | 1.28.1 |
| **Библиотеки** | SQLAlchemy, psycopg2-binary, Pydantic, requests, pandas, plotly | |

# Архитектура решения

```mermaid
graph TD
    %% Определение цветов
    classDef config fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef db fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef app fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef frontend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef user fill:#ffebee,stroke:#c62828,stroke-width:2px;

    subgraph K8s_Cluster ["K8s Cluster (Minikube)"]
        
        subgraph Configs ["Конфигурация"]
            SEC["postgres-secret\n(пароль БД)"]
            CM["postgres-configmap\n(настройки БД)"]
            SA["document-archive-sa\n(ServiceAccount)"]
        end

        subgraph DataLayer ["Слой данных"]
            PVC["postgres-pvc\n(PersistentVolumeClaim 5Gi)"]
            DB_POD("PostgreSQL Pod\npostgres:15-alpine")
            DB_SVC{"postgres-service\n(ClusterIP:5432)"}
        end

        subgraph BackendLayer ["Слой бэкенда"]
            BACKEND_POD1("Backend Pod 1\nFastAPI")
            BACKEND_POD2("Backend Pod 2\nFastAPI")
            BACKEND_SVC{"backend-service\n(ClusterIP:8000)"}
        end

        subgraph FrontendLayer ["Слой фронтенда"]
            FRONTEND_POD("Frontend Pod\nStreamlit")
            FRONTEND_SVC{"frontend-service\n(NodePort:30001)"}
        end

        %% Связи
        SEC -.-> DB_POD:::config
        SEC -.-> BACKEND_POD1:::config
        SEC -.-> BACKEND_POD2:::config
        CM -.-> DB_POD:::config
        SA -.-> BACKEND_POD1:::app
        SA -.-> BACKEND_POD2:::app
        SA -.-> FRONTEND_POD:::frontend
        
        PVC --- DB_POD:::db
        DB_POD --- DB_SVC:::db
        
        BACKEND_POD1 -->|"SQLAlchemy\nCRUD операции"| DB_SVC:::app
        BACKEND_POD2 -->|"SQLAlchemy\nCRUD операции"| DB_SVC:::app
        BACKEND_SVC --- BACKEND_POD1
        BACKEND_SVC --- BACKEND_POD2
        
        FRONTEND_POD -->|"HTTP Requests\nREST API"| BACKEND_SVC:::frontend
    end

    User(("Пользователь")) -->|"http://192.168.49.2:30001\nПросмотр/Создание/Редактирование"| FRONTEND_SVC:::user

    %% Применение стилей
    class SEC,CM,SA config;
    class PVC,DB_POD,DB_SVC db;
    class BACKEND_POD1,BACKEND_POD2,BACKEND_SVC app;
    class FRONTEND_POD,FRONTEND_SVC frontend;
    class User user;
```

# Таблица пояснения компонентов архитектуры

| Блок | Компонент | Краткое пояснение |
|------|-----------|-------------------|
| **Configs** | Secret / ConfigMap / ServiceAccount | Secret хранит пароль PostgreSQL. ConfigMap содержит настройки базы данных (имя БД, пользователь). ServiceAccount предоставляет права доступа для подов бэкенда и фронтенда в кластере. |
| **DataLayer** | PostgreSQL / PVC | База данных для хранения документов, метаданных, истории изменений и файлов (BLOB). PVC 5Gi обеспечивает сохранность данных при перезапуске. |
| **BackendLayer** | FastAPI (2 реплики) | REST API сервис, реализующий CRUD операции, управление версиями, историю изменений, загрузку/скачивание файлов. Две реплики обеспечивают отказоустойчивость. |
| **FrontendLayer** | Streamlit | Пользовательский интерфейс для просмотра, создания, редактирования, удаления документов, просмотра статистики и журнала действий. Доступен через NodePort 30001. |
| **User** | Пользователь | Сотрудник организации, работающий с документами через веб-интерфейс (просмотр, создание, редактирование, удаление). |

# Структура проекта

# Исходные коды

## backend/Dockerfile

Сборка Docker образа бэкенда (Python 3.11, установка зависимостей, запуск uvicorn)

```
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## backend/database.py

Подключение к PostgreSQL, создание сессий SQLAlchemy, настройка движка БД

```
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/documentdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## backend/main.py

Основной файл приложения FastAPI: реализация всех CRUD операций, загрузка/скачивание файлов, история версий, статистика

```
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from typing import List, Optional
import os
import io
from datetime import datetime, timedelta
import json
 
from database import engine, get_db, Base
from models import Document, DocumentType, DocumentStatus, DocumentHistory
from schemas import (
    DocumentCreate, DocumentUpdate, DocumentResponse, 
    DocumentStats, DocumentHistoryResponse
)
 
# Create tables
Base.metadata.create_all(bind=engine)
 
app = FastAPI(title="Архив документов API", version="2.0.0")
 
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Create upload directory
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
 
# Вспомогательная функция для записи истории
def add_history(db: Session, doc_id: int, action: str, old_value: str, new_value: str, changed_by: str = "system"):
    history = DocumentHistory(
        document_id=doc_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by
    )
    db.add(history)
    db.commit()
 
@app.post("/documents/", response_model=DocumentResponse)
async def create_document(
    title: str = Form(...),
    filename: str = Form(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    status: DocumentStatus = Form(DocumentStatus.DRAFT),
    description: str = Form(None),
    tags: str = Form(None),
    is_favorite: bool = Form(False),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Сохраняем файл
    file_content = None
    file_size = 0
    mime_type = None
    
    if file:
        file_content = await file.read()
        file_size = len(file_content)
        mime_type = file.content_type
    
    db_document = Document(
        filename=filename,
        title=title,
        document_type=document_type,
        status=status,
        description=description,
        tags=tags,
        is_favorite=is_favorite,
        file_size=file_size,
        file_content=file_content,
        mime_type=mime_type
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # Записываем историю
    add_history(db, db_document.id, "create", "", f"Создан документ: {title}", "system")
    
    return db_document
 
@app.get("/documents/", response_model=List[DocumentResponse])
def read_documents(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    doc_type: Optional[DocumentType] = None,
    status: Optional[DocumentStatus] = None,
    favorite_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Document).filter(Document.status != DocumentStatus.DELETED)
    
    if search:
        query = query.filter(
            or_(
                Document.title.ilike(f"%{search}%"),
                Document.filename.ilike(f"%{search}%"),
                Document.description.ilike(f"%{search}%"),
                Document.tags.ilike(f"%{search}%")
            )
        )
    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if status:
        query = query.filter(Document.status == status)
    if favorite_only:
        query = query.filter(Document.is_favorite == True)
    
    documents = query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
    return documents
 
@app.get("/documents/{document_id}", response_model=DocumentResponse)
def read_document(document_id: int, db: Session = Depends(get_db)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None or db_document.status == DocumentStatus.DELETED:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return db_document
 
@app.get("/documents/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None or not db_document.file_content:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return StreamingResponse(
        io.BytesIO(db_document.file_content),
        media_type=db_document.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={db_document.filename}"}
    )
 
@app.get("/documents/{document_id}/preview")
def preview_document(document_id: int, db: Session = Depends(get_db)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None or not db_document.file_content:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return StreamingResponse(
        io.BytesIO(db_document.file_content),
        media_type=db_document.mime_type or "application/octet-stream"
    )
 
@app.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int, 
    title: str = Form(None),
    document_type: DocumentType = Form(None),
    status: DocumentStatus = Form(None),
    description: str = Form(None),
    tags: str = Form(None),
    is_favorite: bool = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    # Сохраняем старые значения для истории
    changes = []
    
    if title and title != db_document.title:
        changes.append(("title", db_document.title, title))
        db_document.title = title
    
    if document_type and document_type != db_document.document_type:
        changes.append(("document_type", db_document.document_type.value, document_type.value))
        db_document.document_type = document_type
    
    if status and status != db_document.status:
        changes.append(("status", db_document.status.value, status.value))
        db_document.status = status
    
    if description is not None and description != db_document.description:
        changes.append(("description", db_document.description or "", description or ""))
        db_document.description = description
    
    if tags is not None and tags != db_document.tags:
        changes.append(("tags", db_document.tags or "", tags or ""))
        db_document.tags = tags
    
    if is_favorite is not None and is_favorite != db_document.is_favorite:
        changes.append(("is_favorite", str(db_document.is_favorite), str(is_favorite)))
        db_document.is_favorite = is_favorite
    
    if file:
        file_content = file.file.read()
        changes.append(("file", f"{db_document.filename} ({db_document.file_size} bytes)", f"{file.filename} ({len(file_content)} bytes)"))
        db_document.file_content = file_content
        db_document.file_size = len(file_content)
        db_document.filename = file.filename
        db_document.mime_type = file.content_type
    
    if changes:
        db_document.version += 1
        db_document.updated_at = datetime.now()
        db.commit()
        db.refresh(db_document)
        
        # Записываем историю изменений
        for field, old, new in changes:
            add_history(db, document_id, "update", old, new, "system")
    
    return db_document
 
@app.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    old_status = db_document.status.value
    db_document.status = DocumentStatus.DELETED
    db.commit()
    
    add_history(db, document_id, "delete", old_status, "Удален", "system")
    
    return {"message": "Документ успешно удален"}
 
@app.get("/documents/{document_id}/history", response_model=List[DocumentHistoryResponse])
def get_document_history(document_id: int, db: Session = Depends(get_db)):
    history = db.query(DocumentHistory).filter(
        DocumentHistory.document_id == document_id
    ).order_by(desc(DocumentHistory.changed_at)).all()
    return history
 
@app.get("/stats/", response_model=DocumentStats)
def get_statistics(db: Session = Depends(get_db)):
    total = db.query(Document).filter(Document.status != DocumentStatus.DELETED).count()
    
    by_type = {}
    for doc_type in DocumentType:
        count = db.query(Document).filter(
            Document.document_type == doc_type, 
            Document.status != DocumentStatus.DELETED
        ).count()
        by_type[doc_type.value] = count
    
    by_status = {}
    for status in DocumentStatus:
        if status != DocumentStatus.DELETED:
            count = db.query(Document).filter(Document.status == status).count()
            by_status[status.value] = count
    
    total_size = db.query(func.sum(Document.file_size)).filter(
        Document.status != DocumentStatus.DELETED
    ).scalar() or 0
    
    avg_version = db.query(func.avg(Document.version)).filter(
        Document.status != DocumentStatus.DELETED
    ).scalar() or 0
    
    # Последние действия
    recent_activity = db.query(DocumentHistory).order_by(
        desc(DocumentHistory.changed_at)
    ).limit(10).all()
    
    recent_activity_list = [
        {
            "action": h.action,
            "document_id": h.document_id,
            "changed_at": h.changed_at.isoformat(),
            "changed_by": h.changed_by
        }
        for h in recent_activity
    ]
    
    return DocumentStats(
        total_documents=total,
        by_type=by_type,
        by_status=by_status,
        total_size_mb=total_size / (1024 * 1024),
        avg_version=round(avg_version, 2),
        recent_activity=recent_activity_list
    )
 
@app.get("/recent/", response_model=List[DocumentResponse])
def get_recent_documents(days: int = 7, limit: int = 10, db: Session = Depends(get_db)):
    cutoff_date = datetime.now() - timedelta(days=days)
    documents = db.query(Document)\
        .filter(
            Document.created_at >= cutoff_date, 
            Document.status != DocumentStatus.DELETED
        )\
        .order_by(desc(Document.created_at))\
        .limit(limit)\
        .all()
    return documents
 
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

## backend/models.py

Модели данных: Document (документы) и DocumentHistory (история изменений) с полями и связями

```
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Boolean, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum
 
class DocumentType(str, enum.Enum):
    CONTRACT = "Договор"
    INVOICE = "Счет"
    REPORT = "Отчет"
    POLICY = "Положение"
    ACT = "Акт"
    ORDER = "Приказ"
    OTHER = "Прочее"
 
class DocumentStatus(str, enum.Enum):
    DRAFT = "Черновик"
    ACTIVE = "Действующий"
    ARCHIVED = "В архиве"
    DELETED = "Удален"
 
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    document_type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)
    version = Column(Integer, default=1)
    file_size = Column(Integer, default=0)
    file_path = Column(String(500))
    file_content = Column(LargeBinary, nullable=True)  # Для хранения файлов в БД
    mime_type = Column(String(100))
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    description = Column(Text)
    tags = Column(String(500))
    is_favorite = Column(Boolean, default=False)
    
    # Связь с историей
    history = relationship("DocumentHistory", back_populates="document", cascade="all, delete-orphan")
 
class DocumentHistory(Base):
    __tablename__ = "document_history"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    action = Column(String(50))  # create, update, status_change, version_upgrade
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(100))
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    document = relationship("Document", back_populates="history")
```

## backend/requirements.txt

Список Python зависимостей: fastapi, uvicorn, sqlalchemy, psycopg2-binary, pydantic, python-multipart

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
python-multipart==0.0.6
asyncpg==0.29.0
alembic==1.12.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-decouple==3.8
celery==5.3.4
redis==5.0.1
```

## backend/schemas.py

Cхемы для валидации данных при создании, обновлении и возврате документов

```
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from models import DocumentType, DocumentStatus
 
class DocumentBase(BaseModel):
    filename: str
    title: str
    document_type: DocumentType = DocumentType.OTHER
    status: DocumentStatus = DocumentStatus.DRAFT
    description: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: bool = False
 
class DocumentCreate(DocumentBase):
    created_by: str = "system"
    file_size: int = 0
    file_path: Optional[str] = None
 
class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    document_type: Optional[DocumentType] = None
    status: Optional[DocumentStatus] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: Optional[bool] = None
 
class DocumentResponse(DocumentBase):
    id: int
    version: int
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    file_size: int
    mime_type: Optional[str]
    
    class Config:
        from_attributes = True
 
class DocumentHistoryResponse(BaseModel):
    id: int
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: str
    changed_at: datetime
 
class DocumentStats(BaseModel):
    total_documents: int
    by_type: dict
    by_status: dict
    total_size_mb: float
    avg_version: float
    recent_activity: List[dict]
```

## frontend/Dockerfile

Сборка Docker образа фронтенда (Python 3.11, установка зависимостей, запуск streamlit)

```
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## backend/app.py

Основное Streamlit приложение: пользовательский интерфейс со списком документов, созданием, редактированием, удалением, статистикой и журналом действий

```
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
 
API_URL = "http://backend:8000"
 
# Настройка страницы
st.set_page_config(
    page_title="Электронный архив документов",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# CSS для красивого оформления
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .document-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        cursor: pointer;
        transition: all 0.3s;
    }
    .document-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .history-item {
        padding: 0.75rem;
        border-left: 3px solid #667eea;
        margin-bottom: 0.5rem;
        background: #f8f9fa;
        border-radius: 0.25rem;
    }
    .activity-item {
        padding: 0.75rem;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-active { background: #d4edda; color: #155724; }
    .badge-draft { background: #fff3cd; color: #856404; }
    .badge-archived { background: #e2e3e5; color: #383d41; }
    .stButton>button {
        width: 100%;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)
 
# Инициализация session state
if 'selected_document' not in st.session_state:
    st.session_state.selected_document = None
if 'view' not in st.session_state:
    st.session_state.view = "list"
if 'show_history' not in st.session_state:
    st.session_state.show_history = False
if 'create_mode' not in st.session_state:
    st.session_state.create_mode = None
 
# Маппинг для русских названий
TYPE_NAMES_RU = {
    "contract": "Договор",
    "invoice": "Счет", 
    "report": "Отчет",
    "policy": "Положение",
    "act": "Акт",
    "order": "Приказ",
    "other": "Прочее"
}
 
STATUS_NAMES_RU = {
    "draft": "Черновик",
    "active": "Действующий",
    "archived": "В архиве",
    "deleted": "Удален"
}
 
TYPE_NAMES_EN = {v: k for k, v in TYPE_NAMES_RU.items()}
STATUS_NAMES_EN = {v: k for k, v in STATUS_NAMES_RU.items()}
 
# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📁 Электронный архив документов</h1>
    <p>Система управления документами с историей версий</p>
</div>
""", unsafe_allow_html=True)
 
# Боковая панель
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/folder-invoices.png", width=80)
    st.markdown("### 📋 Навигация")
    
    menu = {
        "list": "📄 Список документов",
        "create": "➕ Создать документ",
        "stats": "📊 Статистика",
        "activity": "🕒 Журнал действий"
    }
    
    selected_menu = st.radio("", list(menu.values()))
    st.session_state.view = [k for k, v in menu.items() if v == selected_menu][0]
    
    st.markdown("---")
    
    # Фильтры для списка документов
    if st.session_state.view == "list":
        st.markdown("### 🔍 Фильтры")
        search_term = st.text_input("Поиск", placeholder="Название, описание...")
        
        col1, col2 = st.columns(2)
        with col1:
            doc_type_ru = st.selectbox("Тип", ["Все"] + list(TYPE_NAMES_RU.values()))
            doc_type = TYPE_NAMES_EN.get(doc_type_ru) if doc_type_ru != "Все" else None
        with col2:
            status_ru = st.selectbox("Статус", ["Все"] + list(STATUS_NAMES_RU.values()))
            status = STATUS_NAMES_EN.get(status_ru) if status_ru != "Все" else None
        
        favorite_only = st.checkbox("⭐ Только избранные")
        
        st.markdown("---")
        
        # Быстрая статистика
        try:
            stats_response = requests.get(f"{API_URL}/stats/")
            if stats_response.status_code == 200:
                stats = stats_response.json()
                st.metric("📄 Всего", stats['total_documents'])
                st.metric("💾 Размер", f"{stats['total_size_mb']:.1f} MB")
        except:
            pass
 
# Основной контент
# ============================================
 
# 1. СПИСОК ДОКУМЕНТОВ
# ============================================
if st.session_state.view == "list":
    st.markdown("### 📄 Список документов")
    
    params = {"skip": 0, "limit": 100}
    if search_term:
        params["search"] = search_term
    if doc_type:
        params["doc_type"] = doc_type
    if status:
        params["status"] = status
    if favorite_only:
        params["favorite_only"] = True
    
    try:
        response = requests.get(f"{API_URL}/documents/", params=params)
        if response.status_code == 200:
            documents = response.json()
            
            if documents:
                # Отображаем карточки документов
                for doc in documents:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 0.8, 0.8, 0.8])
                        
                        with col1:
                            status_class = "active" if doc['status'] == "active" else "draft" if doc['status'] == "draft" else "archived"
                            st.markdown(f"""
                            <div class="document-card">
                                <b>📄 {doc['title']}</b><br>
                                <small>📁 {TYPE_NAMES_RU.get(doc['document_type'], doc['document_type'])} | 
                                🔖 <span class="badge badge-{status_class}">{STATUS_NAMES_RU.get(doc['status'], doc['status'])}</span> | 
                                📅 {doc['created_at'][:10]}</small>
                                {'<br><small>⭐ Избранное</small>' if doc['is_favorite'] else ''}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            if st.button("👁️", key=f"view_{doc['id']}", help="Просмотр"):
                                st.session_state.selected_document = doc['id']
                                st.session_state.show_history = False
                                st.rerun()
                        
                        with col3:
                            if st.button("✏️", key=f"edit_{doc['id']}", help="Редактировать"):
                                st.session_state.selected_document = doc['id']
                                st.session_state.view = "create"
                                st.session_state.create_mode = "edit"
                                st.rerun()
                        
                        with col4:
                            if st.button("📜", key=f"history_{doc['id']}", help="История"):
                                st.session_state.selected_document = doc['id']
                                st.session_state.show_history = True
                                st.rerun()
                        
                        with col5:
                            if st.button("🗑️", key=f"delete_{doc['id']}", help="Удалить"):
                                if st.warning(f"Удалить документ {doc['title']}?"):
                                    del_response = requests.delete(f"{API_URL}/documents/{doc['id']}")
                                    if del_response.status_code == 200:
                                        st.success("Документ удален")
                                        st.rerun()
                
                # Модальное окно просмотра документа
                if st.session_state.selected_document and not st.session_state.show_history:
                    doc = next((d for d in documents if d['id'] == st.session_state.selected_document), None)
                    if doc:
                        st.markdown("---")
                        st.markdown("### 📄 Детали документа")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Название:**", doc['title'])
                            st.write("**Файл:**", doc['filename'])
                            st.write("**Тип:**", TYPE_NAMES_RU.get(doc['document_type'], doc['document_type']))
                            st.write("**Статус:**", STATUS_NAMES_RU.get(doc['status'], doc['status']))
                            st.write("**Версия:**", doc['version'])
                        with col2:
                            st.write("**Создан:**", doc['created_at'][:19])
                            st.write("**Обновлен:**", doc['updated_at'][:19] if doc['updated_at'] else "—")
                            st.write("**Размер:**", f"{doc['file_size'] / 1024:.2f} KB" if doc['file_size'] > 0 else "—")
                            st.write("**Теги:**", doc['tags'] or "—")
                            st.write("**Описание:**", doc['description'] or "—")
                        
                        if st.button("Закрыть", key="close_view"):
                            st.session_state.selected_document = None
                            st.rerun()
                
                # История документа
                if st.session_state.selected_document and st.session_state.show_history:
                    st.markdown("---")
                    st.markdown("### 📜 История изменений")
                    
                    history_response = requests.get(f"{API_URL}/documents/{st.session_state.selected_document}/history")
                    if history_response.status_code == 200:
                        history = history_response.json()
                        if history:
                            for h in history:
                                action_icon = {
                                    "create": "➕ Создание",
                                    "update": "✏️ Изменение",
                                    "delete": "🗑️ Удаление"
                                }.get(h['action'], h['action'])
                                
                                st.markdown(f"""
                                <div class="history-item">
                                    <b>{action_icon}</b>
                                    <span style="float: right;">🕒 {h['changed_at'][:19]}</span><br>
                                    <small>👤 {h['changed_by']}</small>
                                    <br><small>📝 {h['new_value']}</small>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("История изменений пуста")
                    
                    if st.button("Закрыть историю"):
                        st.session_state.selected_document = None
                        st.session_state.show_history = False
                        st.rerun()
            else:
                st.info("📭 Документы не найдены")
        else:
            st.error("❌ Не удалось загрузить документы")
    except Exception as e:
        st.error(f"❌ Ошибка: {e}")
 
# 2. СОЗДАНИЕ/РЕДАКТИРОВАНИЕ ДОКУМЕНТА
# ============================================
elif st.session_state.view == "create":
    if st.session_state.create_mode == "edit":
        st.markdown("### ✏️ Редактирование документа")
        
        # Загружаем документ для редактирования
        try:
            response = requests.get(f"{API_URL}/documents/{st.session_state.selected_document}")
            if response.status_code == 200:
                doc = response.json()
                
                with st.form("edit_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        title = st.text_input("Название *", value=doc['title'])
                        filename = st.text_input("Имя файла *", value=doc['filename'])
                        doc_type_ru = st.selectbox("Тип", list(TYPE_NAMES_RU.values()), 
                                                   index=list(TYPE_NAMES_RU.values()).index(TYPE_NAMES_RU.get(doc['document_type'], "Прочее")))
                    
                    with col2:
                        status_ru = st.selectbox("Статус", list(STATUS_NAMES_RU.values()),
                                                index=list(STATUS_NAMES_RU.values()).index(STATUS_NAMES_RU.get(doc['status'], "Черновик")))
                        tags = st.text_input("Теги", value=doc['tags'] or "")
                        is_favorite = st.checkbox("⭐ В избранное", value=doc['is_favorite'])
                    
                    description = st.text_area("Описание", value=doc['description'] or "")
                    uploaded_file = st.file_uploader("📎 Загрузить новый файл (оставьте пустым, чтобы не менять)", 
                                                     type=['pdf', 'docx', 'txt', 'jpg', 'png', 'xlsx'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("💾 Сохранить изменения")
                    with col2:
                        cancelled = st.form_submit_button("❌ Отмена")
                    
                    if submitted:
                        data = {
                            "title": title,
                            "filename": filename,
                            "document_type": TYPE_NAMES_EN[doc_type_ru],
                            "status": STATUS_NAMES_EN[status_ru],
                            "tags": tags,
                            "description": description,
                            "is_favorite": str(is_favorite).lower()
                        }
                        
                        files = None
                        if uploaded_file:
                            files = {"file": uploaded_file}
                        
                        try:
                            response = requests.put(f"{API_URL}/documents/{st.session_state.selected_document}", 
                                                   data=data, files=files)
                            if response.status_code == 200:
                                st.success("✅ Документ обновлен!")
                                st.session_state.view = "list"
                                st.session_state.create_mode = None
                                st.session_state.selected_document = None
                                st.rerun()
                            else:
                                st.error(f"❌ Ошибка: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Ошибка: {e}")
                    
                    if cancelled:
                        st.session_state.view = "list"
                        st.session_state.create_mode = None
                        st.session_state.selected_document = None
                        st.rerun()
        except Exception as e:
            st.error(f"❌ Ошибка загрузки документа: {e}")
    
    else:
        st.markdown("### ➕ Создание нового документа")
        
        # Выбор способа создания
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Создать без файла", use_container_width=True):
                st.session_state.create_mode = "no_file"
        with col2:
            if st.button("📎 Создать с файлом", use_container_width=True):
                st.session_state.create_mode = "with_file"
        
        st.markdown("---")
        
        if st.session_state.create_mode == "no_file":
            st.info("📝 Создание документа без прикрепленного файла")
            with st.form("create_form_no_file"):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("Название *")
                    filename = st.text_input("Имя файла *")
                
                with col2:
                    doc_type_ru = st.selectbox("Тип", list(TYPE_NAMES_RU.values()))
                    status_ru = st.selectbox("Статус", list(STATUS_NAMES_RU.values()))
                
                description = st.text_area("Описание")
                tags = st.text_input("Теги")
                is_favorite = st.checkbox("⭐ В избранное")
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("✅ Создать")
                with col2:
                    cancelled = st.form_submit_button("❌ Отмена")
                
                if submitted:
                    if not title or not filename:
                        st.error("⚠️ Заполните название и имя файла")
                    else:
                        data = {
                            "title": title,
                            "filename": filename,
                            "document_type": TYPE_NAMES_EN[doc_type_ru],
                            "status": STATUS_NAMES_EN[status_ru],
                            "description": description,
                            "tags": tags,
                            "is_favorite": str(is_favorite).lower()
                        }
                        
                        try:
                            response = requests.post(f"{API_URL}/documents/", data=data)
                            if response.status_code == 200:
                                st.success("✅ Документ создан!")
                                st.balloons()
                                st.session_state.view = "list"
                                st.session_state.create_mode = None
                                st.rerun()
                            else:
                                st.error(f"❌ Ошибка: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Ошибка: {e}")
                
                if cancelled:
                    st.session_state.create_mode = None
                    st.rerun()
        
        elif st.session_state.create_mode == "with_file":
            st.info("📎 Создание документа с прикрепленным файлом")
            with st.form("create_form_with_file"):
                col1, col2 = st.columns(2)
                
                with col1:
                    title = st.text_input("Название *")
                    filename = st.text_input("Имя файла *")
                
                with col2:
                    doc_type_ru = st.selectbox("Тип", list(TYPE_NAMES_RU.values()))
                    status_ru = st.selectbox("Статус", list(STATUS_NAMES_RU.values()))
                
                description = st.text_area("Описание")
                tags = st.text_input("Теги")
                is_favorite = st.checkbox("⭐ В избранное")
                uploaded_file = st.file_uploader("📎 Выберите файл", type=['pdf', 'docx', 'txt', 'jpg', 'png', 'xlsx'])
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("✅ Создать")
                with col2:
                    cancelled = st.form_submit_button("❌ Отмена")
                
                if submitted:
                    if not title or not filename:
                        st.error("⚠️ Заполните название и имя файла")
                    elif not uploaded_file:
                        st.error("⚠️ Выберите файл для загрузки")
                    else:
                        data = {
                            "title": title,
                            "filename": filename,
                            "document_type": TYPE_NAMES_EN[doc_type_ru],
                            "status": STATUS_NAMES_EN[status_ru],
                            "description": description,
                            "tags": tags,
                            "is_favorite": str(is_favorite).lower()
                        }
                        files = {"file": uploaded_file}
                        
                        try:
                            response = requests.post(f"{API_URL}/documents/", data=data, files=files)
                            if response.status_code == 200:
                                st.success("✅ Документ создан с файлом!")
                                st.balloons()
                                st.session_state.view = "list"
                                st.session_state.create_mode = None
                                st.rerun()
                            else:
                                st.error(f"❌ Ошибка: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Ошибка: {e}")
                
                if cancelled:
                    st.session_state.create_mode = None
                    st.rerun()
 
# 3. СТАТИСТИКА
# ============================================
elif st.session_state.view == "stats":
    st.markdown("### 📊 Статистика и аналитика")
    
    try:
        response = requests.get(f"{API_URL}/stats/")
        if response.status_code == 200:
            stats = response.json()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <h2>📄</h2>
                    <h2>{stats['total_documents']}</h2>
                    <p>Всего документов</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <h2>💾</h2>
                    <h2>{stats['total_size_mb']:.1f} MB</h2>
                    <p>Общий размер</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <h2>🔢</h2>
                    <h2>{stats['avg_version']}</h2>
                    <p>Средняя версия</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                    active_count = stats['by_status'].get('active', 0)
                    st.markdown(f"""
                    <div class="stat-card">
                        <h2>✅</h2>
                        <h2>{active_count}</h2>
                        <p>Действующих</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Распределение по типам")
                type_data = {TYPE_NAMES_RU.get(k, k): v for k, v in stats['by_type'].items() if v > 0}
                if type_data:
                    fig = px.pie(values=list(type_data.values()), names=list(type_data.keys()), 
                                title="Документы по типам",
                                color_discrete_sequence=px.colors.qualitative.Set3)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 📊 Статусы документов")
                status_data = {STATUS_NAMES_RU.get(k, k): v for k, v in stats['by_status'].items() if v > 0 and k != 'deleted'}
                if status_data:
                    fig = px.bar(x=list(status_data.keys()), y=list(status_data.values()), 
                                title="Документы по статусам",
                                color=list(status_data.keys()),
                                color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📋 Детальная статистика")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**По типам:**")
                for doc_type, count in stats['by_type'].items():
                    if count > 0:
                        st.write(f"- {TYPE_NAMES_RU.get(doc_type, doc_type)}: {count}")
            
            with col2:
                st.markdown("**По статусам:**")
                for status, count in stats['by_status'].items():
                    if count > 0 and status != 'deleted':
                        st.write(f"- {STATUS_NAMES_RU.get(status, status)}: {count}")
        else:
            st.error("❌ Не удалось загрузить статистику")
    except Exception as e:
        st.error(f"❌ Ошибка: {e}")
 
# 4. ЖУРНАЛ ДЕЙСТВИЙ
# ============================================
elif st.session_state.view == "activity":
    st.markdown("### 🕒 Журнал действий")
    
    try:
        response = requests.get(f"{API_URL}/stats/")
        if response.status_code == 200:
            stats = response.json()
            recent_activity = stats.get('recent_activity', [])
            
            if recent_activity:
                for activity in recent_activity:
                    action_icon = {
                        "create": "➕ Создание документа",
                        "update": "✏️ Редактирование",
                        "delete": "🗑️ Удаление"
                    }.get(activity['action'], "📌 Действие")
                    
                    time = datetime.fromisoformat(activity['changed_at']).strftime('%d.%m.%Y %H:%M:%S')
                    
                    st.markdown(f"""
                    <div class="activity-item">
                        <b>{action_icon}</b>
                        <span style="float: right;">🕒 {time}</span><br>
                        <small>Документ #{activity['document_id']}</small><br>
                        <small>👤 {activity['changed_by']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📭 Журнал действий пуст")
        else:
            st.error("❌ Не удалось загрузить журнал")
    except Exception as e:
        st.error(f"❌ Ошибка: {e}")
 
# Футер
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; padding: 1rem;">
    📁 Электронный архив документов | Система управления документами
</div>
""", unsafe_allow_html=True)
```

## frontend/requirements.txt

Список Python зависимостей: streamlit, requests, pandas, plotly

```
streamlit==1.28.1
requests==2.31.0
pandas==2.1.3
plotly==5.18.0
python-dateutil==2.8.2
pillow==10.1.0
```

## Манифесты Kubernets

| Файл | Описание |
|------|----------|
| `k8s/namespace.yaml` | Создает пространство имен `document-archive` для изоляции всех ресурсов приложения |
| `k8s/serviceaccount.yaml` | Создает ServiceAccount `document-archive-sa`, Role и RoleBinding для управления доступом подов к Kubernetes API |
| `k8s/postgres-configmap.yaml` | Хранит переменные окружения для PostgreSQL: POSTGRES_DB, POSTGRES_USER |
| `k8s/postgres-secret.yaml` | Хранит пароль PostgreSQL в зашифрованном виде (base64) |
| `k8s/postgres-pvc.yaml` | PVC для сохранения данных PostgreSQL при перезапусках и сбоях |
| `k8s/postgres-deployment.yaml` | Развертывание PostgreSQL: порт 5432, подключение PVC, переменные окружения из ConfigMap и Secret |
| `k8s/postgres-service.yaml` | ClusterIP сервис для внутреннего доступа бэкенда к PostgreSQL (порт 5432) |
| `k8s/backend-deployment.yaml` | Развертывание бэкенда: 2 реплики FastAPI, порт 8000, переменная DATABASE_URL |
| `k8s/backend-service.yaml` | ClusterIP сервис для доступа фронтенда к бэкенду (порт 8000) |
| `k8s/frontend-deployment.yaml` | Развертывание фронтенда: Streamlit, порт 8501, переменная API_URL |
| `k8s/frontend-service.yaml` | NodePort сервис для внешнего доступа пользователей к приложению (порт 30001) |

# Запуск

Запускаем миникуб:

<img width="975" height="464" alt="Снимок экрана 2026-03-31 094851" src="https://github.com/user-attachments/assets/8aa7bdb3-cd02-45f7-a380-77fe42bdf9cb" />

Переходим в окружение:

<img width="953" height="21" alt="Снимок экрана 2026-03-31 094913" src="https://github.com/user-attachments/assets/f98e7217-daa0-4d1e-8d51-c3fc75a19735" />

Собираем кастомный образ для бекэнда:

<img width="967" height="427" alt="Снимок экрана 2026-03-31 094923" src="https://github.com/user-attachments/assets/161cdc5f-98b4-4f69-83e6-45c874c5e54b" />

Собираем кастомный образ для фронтэнда:

<img width="969" height="329" alt="Снимок экрана 2026-03-31 094947" src="https://github.com/user-attachments/assets/ab4f26a3-3352-4d17-b202-81178a0cd0f5" />

Применяем манифесты Kubernets:

<img width="849" height="432" alt="Снимок экрана 2026-03-31 095022" src="https://github.com/user-attachments/assets/9a2dad28-f396-4aa9-a443-c1aac970ed2e" />

Запускаем приложение:

<img width="966" height="123" alt="Снимок экрана 2026-03-31 095104" src="https://github.com/user-attachments/assets/4f6e5cea-8db1-4808-9112-2d7a42051d6c" />

# Результат

Перейдем в браузер и посмотрим на приложение.

Приложение имеет 4 раздела. Первый раздел содержит список документов, созданных в приложении:

<img width="1212" height="736" alt="image" src="https://github.com/user-attachments/assets/f53b6a39-9218-4f67-bc73-ed938d59fdb3" />

На этой странице доступен поиск по наименованию, фильтрация по типу документа, сортировка по нескольким параметрам и возможность отображать только избранные документы.

Также здесь можно просмотреть содержимое документа и отредактировать его:

<img width="870" height="462" alt="image" src="https://github.com/user-attachments/assets/b8f1cd0c-94b5-43cc-9804-cc529b847219" />

Тут же документ можно удалить, если он больше не актуален.

Второй раздел - создание документов. Доступно для варианта - с прикреплением файла и без:

<img width="1206" height="646" alt="image" src="https://github.com/user-attachments/assets/9b93f9a9-cfa7-4ee7-bdda-f64dca5b4263" />

В разделе "Создать документ" необходимо заполнить все поля и нажать на кнопку "Создать документ"

В разделе "Загрузить файл" можно дополнительно прикрепить файл, который будет приложением:

<img width="922" height="658" alt="image" src="https://github.com/user-attachments/assets/ff08bec6-c241-40fb-adc6-45dde4c8d893" />

В разделе "Статистика" можно посмотреть дашборд:

<img width="1203" height="690" alt="image" src="https://github.com/user-attachments/assets/09dd38d8-78df-4012-bc65-8705e6d7d887" />

<img width="959" height="443" alt="image" src="https://github.com/user-attachments/assets/e6978a0c-4227-4583-bc4d-b908e3e6ceb7" />

<img width="926" height="406" alt="image" src="https://github.com/user-attachments/assets/67d5af16-2d85-402d-a7ae-ad0165050222" />

<img width="924" height="428" alt="image" src="https://github.com/user-attachments/assets/63d2caf1-42f9-48eb-a980-70ed5602a8e0" />

В разделе журнал действий можно просмотреть историю взаимодействия с файлами и при необходимости выгрузить в csv файл:

<img width="944" height="529" alt="image" src="https://github.com/user-attachments/assets/e277b97e-fb5c-4e18-a012-897fcec7c06a" />

<img width="1078" height="391" alt="image" src="https://github.com/user-attachments/assets/5c2fdf4e-69d6-45d2-8ad7-6759af9b4ca6" />

