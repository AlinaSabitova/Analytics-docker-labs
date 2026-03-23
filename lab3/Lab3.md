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

## Схема таблицы данных

```mermaid
erDiagram
    sales {
        int id PK
        varchar(100) product
        varchar(50) category
        int quantity
        numeric price
        date sale_date
        varchar(50) region
        varchar(50) customer_type
        varchar(50) payment_method
    }
```

## Распределение данных

```mermaid
pie title "Распределение продаж по городам"
    "Москва" : 45
    "Санкт-Петербург" : 30
    "Екатеринбург" : 12
    "Казань" : 8
    "Новосибирск" : 5
```

```mermaid
pie title "Выручка по типам клиентов"
    "VIP" : 60
    "Постоянный" : 30
    "Новый" : 10
```

```mermaid
pie title "Выручка по категориям"
    "Смартфоны" : 60
    "Планшеты" : 25
    "Электроника" : 8
    "Аксессуары" : 7
```

## Сетевая архитектура

```mermaid
graph LR
    subgraph "Хост-машина (Ubuntu)"
        BROWSER[Браузер<br/>localhost:30088]
        MINIKUBE_IP[Minikube IP<br/>192.168.49.2]
    end

    subgraph "Minikube Cluster"
        NODEPORT[NodePort<br/>30088]
        CLUSTER_IP[ClusterIP<br/>10.110.59.206:8088]
        POSTGRES_IP[ClusterIP<br/>10.105.188.46:5432]
        REDIS_IP[ClusterIP<br/>10.106.84.227:6379]
    end

    BROWSER -->|HTTP| MINIKUBE_IP
    MINIKUBE_IP --> NODEPORT
    NODEPORT --> CLUSTER_IP
    CLUSTER_IP -->|Internal| POSTGRES_IP
    CLUSTER_IP -->|Internal| REDIS_IP
```

## Компоненты системы

### Основные компоненты

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Superset** | Apache Superset | 6.0.0 | BI-платформа, визуализация данных |
| **PostgreSQL** | PostgreSQL | 16 | Хранение данных и метаданных |
| **Redis** | Redis | 7-alpine | Кэширование, сессии, брокер |
| **Data Generator** | Python | 3.12 | Генерация тестовых данных |

### Сетевые сервисы

| Сервис | Тип | Порт | Доступ |
|--------|-----|------|--------|
| superset-service | NodePort | 8088:30088 | Внешний (http://192.168.49.2:30088) |
| postgres-service | ClusterIP | 5432 | Внутри кластера |
| redis-service | ClusterIP | 6379 | Внутри кластера |

### Хранилища

| Название | Тип | Размер | Монтирование |
|----------|-----|--------|--------------|
| postgres-pvc | PersistentVolumeClaim | 3Gi | /var/lib/postgresql/data |
| postgres-storage | hostPath | 3Gi | /tmp/postgres-data |

## Потоки данных

```mermaid
flowchart TD
    subgraph "Источники данных"
        GEN[Data Generator Job]
    end

    subgraph "Хранилище"
        DB[(PostgreSQL<br/>sales table)]
    end

    subgraph "Обработка"
        SUP[Superset<br/>BI Platform]
        CACHE[(Redis<br/>Cache)]
    end

    subgraph "Потребители"
        USER[Пользователи]
    end

    GEN -->|Insert 1000+ records| DB
    DB -->|Read data| SUP
    SUP -->|Cache results| CACHE
    CACHE -->|Serve cached| SUP
    SUP -->|Visualize| USER
    USER -->|Interactive queries| SUP
```

## Технический стек

| Категория | Технологии |
|-----------|------------|
| **ОС** | Ubuntu 24.04 LTS |
| **Контейнеризация** | Docker 24.x |
| **Оркестрация** | Minikube, Kubernetes (kubectl) |
| **База данных** | PostgreSQL 16, Redis 7 |
| **Язык программирования** | Python 3.10 (Superset), Python 3.12 (Generator) |
| **Аналитическая среда** | Apache Superset 6.0.0 |
| **Библиотеки** | psycopg2-binary, flask, sqlalchemy, redis |

