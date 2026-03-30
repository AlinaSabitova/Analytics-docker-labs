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
# Электронный архив документов

## Технический стек и окружение

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

## Архитектура решения

```mermaid
graph TD
    classDef db fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef app fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef frontend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef user fill:#ffebee,stroke:#c62828,stroke-width:2px;

    subgraph K8s_Cluster ["Kubernetes Cluster (Minikube)"]
        
        subgraph DataLayer ["Слой данных"]
            DB_POD("PostgreSQL Pod\npostgres:15-alpine")
            DB_SVC{"postgres-service\n(ClusterIP:5432)"}
            PVC["PVC 5Gi\n(PersistentVolume)"]
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

        PVC --- DB_POD:::db
        DB_POD --- DB_SVC:::db
        
        BACKEND_POD1 -->|"SQLAlchemy"| DB_SVC:::app
        BACKEND_POD2 -->|"SQLAlchemy"| DB_SVC:::app
        BACKEND_SVC --- BACKEND_POD1
        BACKEND_SVC --- BACKEND_POD2
        
        FRONTEND_POD -->|"HTTP REST API"| BACKEND_SVC:::frontend
    end

    User(("Пользователь")) -->|"http://192.168.49.2:30001"| FRONTEND_SVC:::user

    class DB_POD,DB_SVC,PVC db;
    class BACKEND_POD1,BACKEND_POD2,BACKEND_SVC app;
    class FRONTEND_POD,FRONTEND_SVC frontend;
    class User user;
```
