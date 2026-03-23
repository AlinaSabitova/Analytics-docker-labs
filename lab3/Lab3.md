# Лабораторная работа 3.1. Развертывание приложения в Kubernetes

# Цель работы

Освоить процесс оркестрации контейнеров. Научиться разворачивать связки сервисов (аналитическое приложение + база данных/интерфейс) в кластере Kubernetes, управлять их масштабированием (Deployment) и сетевой доступностью (Service).

# Индивидуальное задание

| Вариант | Основной сервис (App) | Вспомогательный сервис (DB/Tool) | Задача |
|---------|----------------------|----------------------------------|--------|
| **12** | **Apache Superset** | **PostgreSQL** | Попытаться развернуть Superset (или облегченную версию) с подключением к БД. |

## Технический стек и окружение

**ОС:** Ubuntu 24.04 LTS

**Контейнеризация:** Docker 24.x

**Оркестрация:** Minikube (Driver: Docker), Kubernetes (kubectl)

**База данных:** PostgreSQL 16, Redis 7

**Язык программирования:** Python 3.10

**Аналитическая среда:** Apache Superset 6.0.0 

**Библиотеки:** psycopg2-binary, flask, sqlalchemy, redis, random, datetime, time

## 3. Архитектура решения

```mermaid
graph TD
    %% Определение цветов
    classDef config fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef db fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef app fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef batch fill:#f1f8e9,stroke:#558b2f,stroke-width:2px;
    classDef cache fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef user fill:#ffebee,stroke:#c62828,stroke-width:2px;

    subgraph K8s_Cluster ["K8s Cluster (Minikube)"]
        
        subgraph Configs ["Конфигурация"]
            SEC["superset-secrets\n(Opaque)"]
            SA["superset-sa\n(ServiceAccount)"]
        end

        subgraph DataLayer ["Слой данных"]
            PVC["postgres-pvc\n(PersistentVolumeClaim)"]
            DB_POD("PostgreSQL Pod\npostgres:16")
            DB_SVC{"postgres-service\n(ClusterIP:5432)"}
        end

        subgraph CacheLayer ["Слой кэширования"]
            CACHE_POD("Redis Pod\nredis:7-alpine")
            CACHE_SVC{"redis-service\n(ClusterIP:6379)"}
        end

        subgraph Analytics ["Слой аналитики"]
            APP_POD("Superset Pod\nmy-superset:v1")
            APP_SVC{"superset-service\n(NodePort:30088)"}
            INIT["Init Container\nsuperset-init\n(миграции + админ)"]
        end

        subgraph DataLoader ["Загрузка данных"]
            JOB("Data Generator Job\nmy-generator:v1")
        end

        %% Связи
        SEC -.-> DB_POD:::config
        SEC -.-> APP_POD:::config
        SA -.-> APP_POD:::app
        PVC --- DB_POD:::db
        DB_POD --- DB_SVC:::db
        CACHE_POD --- CACHE_SVC:::cache
        
        JOB -->|"INSERT 1000+ rows"| DB_SVC:::batch
        APP_POD -->|"SQLAlchemy\n(metadata + data)"| DB_SVC:::app
        APP_POD -->|"Cache & Sessions"| CACHE_SVC:::app
        APP_POD --- INIT:::app
    end

    User(("Аналитик")) -->|"http://192.168.49.2:30088\nadmin/admin"| APP_SVC:::user

    %% Применение стилей
    class SEC,SA config;
    class PVC,DB_POD,DB_SVC db;
    class APP_POD,APP_SVC,INIT app;
    class CACHE_POD,CACHE_SVC cache;
    class JOB batch;
    class User user;
```

## Таблица пояснения компонентов архитектуры

| Блок | Компонент | Краткое пояснение |
|------|-----------|-------------------|
| **Configs** | Secret / ServiceAccount | Secret хранит пароли (PostgreSQL, Redis, Superset). ServiceAccount предоставляет права доступа для Superset. |
| **Database** | PostgreSQL / hostPath | База данных для хранения метаданных Superset и таблицы sales. hostPath обеспечивает сохранность данных в /tmp/postgres-data. |
| **Cache** | Redis | Кэш для ускорения запросов и хранения сессий пользователей. |
| **Analytics** | Superset | BI-платформа для визуализации данных. Использует InitContainer для миграций БД и создания администратора. |
| **Data** | Data Generator Job | Однократный процесс, наполняющий БД тестовыми данными (1000+ записей о продажах). |
| **User** | Аналитик | Внешний пользователь, получающий доступ к Superset через NodePort (порт 30088). |
