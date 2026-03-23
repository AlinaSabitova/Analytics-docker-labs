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

# Архитектура решения

# Архитектура сервиса аналитики данных

## Диаграмма архитектуры

```mermaid
graph TB
    subgraph "Внешний доступ"
        USER[Пользователь]
        BROWSER[Браузер]
    end

    subgraph "Kubernetes Cluster (Minikube)"
        
        subgraph "Services Layer"
            SS[superset-service<br/>NodePort:30088]
            PS[postgres-service<br/>ClusterIP:5432]
            RS[redis-service<br/>ClusterIP:6379]
        end

        subgraph "Application Layer"
            SUP[Superset Pod<br/>my-superset:v1<br/>Port:8088]
            INIT[Init Container<br/>superset-init<br/>- DB migrations<br/>- Admin creation]
        end

        subgraph "Data Layer"
            PG[PostgreSQL Pod<br/>postgres:16<br/>Port:5432<br/>DB: superset]
            RD[Redis Pod<br/>redis:7-alpine<br/>Port:6379<br/>Cache & Broker]
            PV[Persistent Volume<br/>hostPath: /tmp/postgres-data<br/>Size: 3Gi]
        end

        subgraph "Batch Processing"
            GEN[Data Generator Job<br/>my-generator:v1<br/>Generates 1000+ records]
        end

        subgraph "Configuration"
            SEC[Secrets<br/>superset-secrets]
            SA[Service Account<br/>superset-sa]
        end

    end

    USER --> BROWSER
    BROWSER -->|HTTP:30088| SS
    SS -->|Forward| SUP
    SUP -->|SQLAlchemy| PS
    SUP -->|Cache/Redis| RS
    PS -->|Mount| PV
    GEN -->|Insert data| PS
    SUP -.->|Init| INIT
    SUP -.->|Uses| SEC
    SUP -.->|Uses| SA
    PG -.->|Uses| SEC
```

## Схема взаимодействия компонентов

```mermaid
sequenceDiagram
    participant User
    participant Superset
    participant Redis
    participant PostgreSQL
    participant Generator

    Note over Generator,PostgreSQL: 1. Инициализация данных
    Generator->>PostgreSQL: Создание таблицы sales
    Generator->>PostgreSQL: Вставка 1000+ записей
    Generator-->>Generator: Job Completed

    Note over User,PostgreSQL: 2. Работа с приложением
    User->>Superset: HTTP запрос (admin/admin)
    Superset->>PostgreSQL: Запрос метаданных
    PostgreSQL-->>Superset: Структура датасетов
    
    User->>Superset: Запрос графика
    Superset->>Redis: Проверка кэша
    Redis-->>Superset: Cache miss
    Superset->>PostgreSQL: Выполнение SQL
    PostgreSQL-->>Superset: Результат
    Superset->>Redis: Сохранение в кэш
    Superset-->>User: Визуализация

    Note over User,PostgreSQL: 3. Повторный запрос (кэш)
    User->>Superset: Тот же график
    Superset->>Redis: Проверка кэша
    Redis-->>Superset: Cache hit
    Superset-->>User: Быстрый ответ из кэша
```

