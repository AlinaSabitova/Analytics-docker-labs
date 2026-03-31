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
graph TB
    subgraph K8s["Kubernetes Cluster (Minikube)"]
        
        subgraph Data["Слой данных"]
            PostgreSQL[("PostgreSQL\npostgres:15-alpine")]
            PVC[("PVC 5Gi\nPersistentVolume")]
        end

        subgraph Backend["Слой бэкенда"]
            API1[("Backend Pod 1\nFastAPI")]
            API2[("Backend Pod 2\nFastAPI")]
        end

        subgraph Frontend["Слой фронтенда"]
            Streamlit[("Frontend Pod\nStreamlit")]
        end

        PVC --> PostgreSQL
        API1 --> PostgreSQL
        API2 --> PostgreSQL
        Streamlit --> API1
        Streamlit --> API2
    end

    User((Пользователь)) --> Streamlit
