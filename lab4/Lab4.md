# Лабораторная работа 4.1. Создание и развертывание полнофункционального приложения

# Цель работы

Применить полученные знания по созданию и развертыванию трехзвенного приложения (Frontend + Backend + Database) в кластере Kubernetes. Научиться организовывать взаимодействие между микросервисами.

# Индивидуальное задание

| Вариант | Название системы | Бизнес-задача | Данные (Пример) |
|---------|------------------|---------------|-----------------|
| 12 | Rocket Launch Analytics | Мониторинг и анализ космических запусков | Название миссии, статус запуска, дата старта, провайдер, изображения ракет |

## Технический стек и окружение

**ОС:** Ubuntu 22.04 LTS

**Контейнеризация:** Docker

**Оркестрация:** Minikube (Driver: Docker), Kubernetes (kubectl)

**База данных:** PostgreSQL 15

**Язык программирования:** Python 3.11

**Backend:** FastAPI, Uvicorn

**Frontend:** Streamlit

**Библиотеки:** SQLAlchemy, psycopg2-binary, Pydantic, requests, pandas, plotly, python-multipart

## Архитектура решения

```mermaid
graph TD
    %% Определение цветов
    classDef config fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef db fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef app fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef frontend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef storage fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
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

        subgraph DataStorage ["Хранение данных"]
            UPLOADS["Uploads Volume\n/var/lib/postgresql/data"]
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
        UPLOADS --- DB_POD:::storage
        
        BACKEND_POD1 -->|"SQLAlchemy\nCRUD операции"| DB_SVC:::app
        BACKEND_POD2 -->|"SQLAlchemy\nCRUD операции"| DB_SVC:::app
        FRONTEND_POD -->|"HTTP Requests\nREST API"| BACKEND_SVC:::frontend
        BACKEND_SVC --- BACKEND_POD1
        BACKEND_SVC --- BACKEND_POD2
    end

    User(("Пользователь\n(Сотрудник)")) -->|"http://192.168.49.2:30001\nПросмотр/Создание/Редактирование"| FRONTEND_SVC:::user
    Admin(("Администратор")) -->|"kubectl\nУправление кластером"| K8s_Cluster:::user

    %% Применение стилей
    class SEC,CM,SA config;
    class PVC,DB_POD,DB_SVC db;
    class BACKEND_POD1,BACKEND_POD2,BACKEND_SVC app;
    class FRONTEND_POD,FRONTEND_SVC frontend;
    class UPLOADS storage;
    class User,Admin user;
```
