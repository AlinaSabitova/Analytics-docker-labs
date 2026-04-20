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
            SEC["superset-secret"]
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
            INIT["Init Container\nsuperset-init"]
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

```mermaid
graph TD
    %% Определение классов стилей
    classDef logic fill:#f9f9f9,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;
    classDef db fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef app fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef search fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef user fill:#ffebee,stroke:#c62828,stroke-width:2px;
    classDef server fill:#eceff1,stroke:#546e7a,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph Gostech_Server ["Сервер Gostech"]
        subgraph Data ["Слой данных"]
            PG1("Postgres\n(Основные данные)"):::db
            PG2("Postgres 2\n(Данные пользователей)"):::db
            MYSQL("MySQL\n(Данные DAHBE)"):::db
        end
    end

    subgraph App_Infra ["Инфраструктура приложений"]
        subgraph Core ["Основные сервисы"]
            APP("Monolith (egisu)\nОсновное приложение"):::app
            USERS("users-service\n(Сервис пользователей)"):::app
        end

        subgraph Search ["Поиск и Логи"]
            OS("OpenSearch"):::search
            KIB("Kibana\n(Визуализация логов)"):::search
            DAHBE("DAHBE\n(Обработчик событий)"):::search
        end

        subgraph Logic ["ЛОГИКА\n(Бизнес-слой)"]
            REALS("reals\n(Процессинг данных)"):::logic
        end
    end

    %% Пользователь
    User(("Пользователь")):::user

    %% Связи
    User -->|HTTP Requests| APP
    APP -->|Запись / Чтение| PG1
    APP -->|Запросы пользователей| USERS
    USERS -->|Хранение профилей| PG2
    
    APP -->|Логирование| OS
    OS -->|Визуализация| KIB
    DAHBE -->|Обработка событий| MYSQL
    DAHBE -->|Индексация| OS
    
    APP -->|Асинхронные события| REALS
    REALS -->|Аналитика / Статистика| DAHBE

    %% Стилизация
    class Gostech_Server server;
    class REALS logic;
    class PG1,PG2,MYSQL db;
    class OS,KIB,DAHBE search;
```


# Таблица пояснения компонентов архитектуры

| Блок | Компонент | Краткое пояснение |
|------|-----------|-------------------|
| **Configs** | Secret / ServiceAccount | Secret хранит пароли (PostgreSQL, Redis, Superset). ServiceAccount предоставляет права доступа для Superset. |
| **Database** | PostgreSQL / PVC | База данных для хранения метаданных Superset и таблицы sales. |
| **Cache** | Redis | Кэш для ускорения запросов и хранения сессий пользователей. |
| **Analytics** | Superset | BI-платформа для визуализации данных. |
| **Data** | Data Generator Job | Однократный процесс, наполняющий БД тестовыми данными (1000 записей о продажах). |
| **User** | Аналитик | Внешний пользователь, получающий доступ к Superset. |

# Исходные коды файлов

## Образ Apache Superset

### `app/Dockerfile`

Dockerfile - для сборки кастомного образа Superset. На основе официального образа apache/superset:6.0.0-dev копирует конфигурационный файл superset_config.py, устанавливает права доступа и указывает путь к нему через переменную окружения:

```
FROM apache/superset:6.0.0-dev
 
USER root
 
COPY superset_config.py /app/superset_config.py
RUN chown superset:superset /app/superset_config.py
 
ENV SUPERSET_CONFIG_PATH=/app/superset_config.py
 
USER superset
```

### `app/superset_config.py`

Конфигурационный файл Apache Superset. Определяет подключение к PostgreSQL через SQLAlchemy, настройки Redis для кэширования, секретный ключ, включение дополнительных функций:
```
import os
from cachelib.redis import RedisCache
 
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "super-secret-key-CHANGE-THIS-9876543210abcdef")
 
# Подключение к PostgreSQL
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{os.environ.get('DB_USER', 'superset')}:"
    f"{os.environ.get('DB_PASS', 'superset123')}@"
    f"{os.environ.get('DB_HOST', 'postgres-service')}:"
    f"{os.environ.get('DB_PORT', '5432')}/"
    f"{os.environ.get('DB_NAME', 'superset')}"
)
 
# Redis 
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-service")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_CELERY_DB = int(os.environ.get("REDIS_CELERY_DB", "1"))
 
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_DB,
}
 
CELERY_CONFIG = {
    "broker_url": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}",
    "result_backend": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}",
}
 
RESULTS_BACKEND = RedisCache(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, key_prefix="superset_results"
)
 
ENABLE_PROXY_FIX = True
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "ALERT_REPORTS": True,
    "EMBEDDED_DASHBOARDS": True,
}
 
SILENCE_FAB_WARNINGS = True
```

### `generator/Dockerfile`

Dockerfile для сборки образа генератора данных. Устанавливает драйвер psycopg2-binary для работы с PostgreSQL и запускает скрипт generator.py:
```
FROM python:3.10-slim
WORKDIR /app
COPY generator.py .
RUN pip install --no-cache-dir psycopg2-binary
CMD ["python", "-u", "generator.py"]
```

### `generator/generator.py`

Скрипт генерации тестовых данных о продажах в магазине электроники:
```
import os
import psycopg2
import random
import time
from datetime import datetime, timedelta
 
# Функция для ожидания подключения к БД
def wait_for_db():
    max_retries = 60
    retry_interval = 5
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "postgres-service"),
                port=os.getenv("DB_PORT", "5432"),
                dbname=os.getenv("DB_NAME", "superset"),
                user=os.getenv("DB_USER", "superset"),
                password=os.getenv("DB_PASS", "superset123")
            )
            conn.close()
            print("✅ База данных доступна")
            return True
        except psycopg2.OperationalError as e:
            print(f"⏳ Ожидание БД... ({i+1}/{max_retries})")
            time.sleep(retry_interval)
    
    print("❌ Не удалось подключиться к БД")
    return False
 
# Ждем подключения к БД
if not wait_for_db():
    exit(1)
 
# Подключение к базе данных
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "postgres-service"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "superset"),
    user=os.getenv("DB_USER", "superset"),
    password=os.getenv("DB_PASS", "superset123")
)
cur = conn.cursor()
 
# Удаляем старую таблицу, если есть
cur.execute("DROP TABLE IF EXISTS sales CASCADE")
 
# Создаем новую таблицу
cur.execute("""
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    product VARCHAR(100),
    category VARCHAR(50),
    quantity INT,
    price NUMERIC(10,2),
    sale_date DATE,
    region VARCHAR(50),
    customer_type VARCHAR(50),
    payment_method VARCHAR(50)
)
""")
 
# Данные для генерации
products = {
    "iPhone 15 Pro": {"category": "Смартфоны", "price": 89999, "weight": 30},
    "Samsung Galaxy S24": {"category": "Смартфоны", "price": 69999, "weight": 30},
    "Планшет iPad Air": {"category": "Планшеты", "price": 69990, "weight": 20},
    "Планшет Samsung Tab": {"category": "Планшеты", "price": 49990, "weight": 15},
    "Ноутбук Dell XPS": {"category": "Электроника", "price": 120000, "weight": 8},
    "Монитор LG UltraWide": {"category": "Мониторы", "price": 45990, "weight": 6},
    "Sony WH-1000XM5": {"category": "Аудио", "price": 24990, "weight": 5},
    "Клавиатура Logitech MX": {"category": "Аксессуары", "price": 8000, "weight": 3},
    "Мышь Razer": {"category": "Аксессуары", "price": 4800, "weight": 2},
    "Чехол для телефона": {"category": "Аксессуары", "price": 800, "weight": 1}
}
 
# Города с весами
cities = {
    "Москва": 45,
    "Санкт-Петербург": 30,
    "Екатеринбург": 12,
    "Казань": 8,
    "Новосибирск": 5
}
 
# Типы клиентов
customer_types = {
    "VIP": 60,
    "Постоянный": 30,
    "Новый": 10
}
 
payment_methods = ["Карта", "Наличные", "Онлайн"]
 
def weighted_choice(weighted_dict):
    items = list(weighted_dict.keys())
    weights = list(weighted_dict.values())
    return random.choices(items, weights=weights)[0]
 
def get_quantity_by_price(price):
    if price >= 100000:
        return random.randint(1, 3)
    elif price >= 50000:
        return random.randint(2, 8)
    elif price >= 20000:
        return random.randint(5, 15)
    else:
        return random.randint(10, 50)
 
print("🔄 Генерация данных...")
total_records = 1000
 
for i in range(total_records):
    product_name = weighted_choice({k: v["weight"] for k, v in products.items()})
    product = products[product_name]
    category = product["category"]
    base_price = product["price"]
    price = round(base_price * random.uniform(0.95, 1.05), 2)
    quantity = get_quantity_by_price(price)
    region = weighted_choice(cities)
    
    if price > 50000:
        cust_weights = {"VIP": 45, "Постоянный": 35, "Новый": 20}
    else:
        cust_weights = customer_types
    customer_type = weighted_choice(cust_weights)
    
    sale_date = (datetime.now() - timedelta(days=random.randint(0, 730))).date()
    
    cur.execute(
        """
        INSERT INTO sales 
        (product, category, quantity, price, sale_date, region, customer_type, payment_method)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            product_name,
            category,
            quantity,
            price,
            sale_date,
            region,
            customer_type,
            random.choice(payment_methods)
        )
    )
 
conn.commit()
 
cur.execute("SELECT COUNT(*) FROM sales")
count = cur.fetchone()[0]
print(f"✅ Создано {count} записей")
 
cur.close()
conn.close()
print("🎉 Генерация данных завершена!")
```

### `k8s/secret.yaml`

Хранит учетные данные для подключения к PostgreSQL (пользователь, пароль, БД) и Redis (хост, порт), а также секретный ключ Superset:
```
apiVersion: v1
kind: Secret
metadata:
  name: superset-secrets
type: Opaque
stringData:
  POSTGRES_USER: superset
  POSTGRES_PASSWORD: superset123
  POSTGRES_DB: superset
  DB_USER: superset
  DB_PASS: superset123
  DB_HOST: postgres-service
  DB_PORT: "5432"
  DB_NAME: superset
  SUPERSET_SECRET_KEY: "super-secret-key-CHANGE-THIS-9876543210abcdef"
  REDIS_HOST: redis-service
  REDIS_PORT: "6379"
  REDIS_DB: "0"
  REDIS_CELERY_DB: "1"
```

### `k8s/serviceaccount.yaml`

ServiceAccount для Superset, используемый для назначения прав доступа внутри кластера:
```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: superset-sa
```

### `k8s/pvc.yaml`

PersistentVolumeClaim (PVC) для PostgreSQL:
```
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 3Gi
```

### `k8s/postgres-deployment.yaml`

Развертывание PostgreSQL. Содержит init-контейнер для исправления прав доступа, переменные окружения из секрета, PVC для хранения данных:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      serviceAccountName: superset-sa
      
      initContainers:
      - name: init-chown
        image: busybox
        command: ['sh', '-c', 'chown -R 999:999 /var/lib/postgresql/data']
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
 
      containers:
      - name: postgres
        image: postgres:16
        imagePullPolicy: IfNotPresent
        
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: superset-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: superset-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: superset-secrets
              key: POSTGRES_DB
 
        ports:
        - containerPort: 5432
          name: postgres
 
        volumeMounts:
        - mountPath: /var/lib/postgresql/data
          name: postgres-storage
 
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

### `k8s/postgres-service.yaml`

Сервис для доступа к PostgreSQL внутри кластера на порту 5432:
```
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### `k8s/superset-deployment.yaml`

Развертывание Apache Superset. Содержит init-контейнер для инициализации БД и основной контейнер с портом 8088:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: superset
spec:
  replicas: 1
  selector:
    matchLabels:
      app: superset
  template:
    metadata:
      labels:
        app: superset
    spec:
      serviceAccountName: superset-sa
 
      initContainers:
      - name: superset-init
        image: my-superset:v1 
        imagePullPolicy: Never
        envFrom:
        - secretRef:
            name: superset-secrets
        command: ["/bin/sh", "-c"]
        args:
        - |
          echo "=== Starting Superset 6.0.0 initialization ===" &&
          superset db upgrade &&
          echo "=== DB upgrade completed ===" &&
          superset fab create-admin \
            --username admin \
            --firstname Admin \
            --lastname User \
            --email admin@example.com \
            --password admin || true &&
          echo "=== Running superset init ===" &&
          superset init &&
          echo "=== Initialization completed successfully ==="
 
      containers:
      - name: superset
        image: my-superset:v1 
        imagePullPolicy: Never
        envFrom:
        - secretRef:
            name: superset-secrets
        ports:
        - containerPort: 8088
          name: http
```

### `k8s/superset-service.yaml`

Сервис для доступа к Superset, открывается на порту 30088:
```
apiVersion: v1
kind: Service
metadata:
  name: superset-service
spec:
  type: NodePort
  selector:
    app: superset
  ports:
  - port: 8088
    targetPort: 8088
    nodePort: 30088
```

### `k8s/redis-deployment.yaml`

Развертывание Redis для кэширования. Запускает один под с Redis 7-alpine на порту 6379:
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
```

### `k8s/redis-service.yaml`

Сервис для доступа к Redis внутри кластера на порту 6379:
```
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### `k8s/generator-job.yaml`

Job для генерации тестовых данных. Запускает контейнер my-generator:v1, который подключается к PostgreSQL и заполняет таблицу `sales` данными:
```
apiVersion: batch/v1
kind: Job
metadata:
  name: data-generator
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: generator
        image: my-generator:v1 
        imagePullPolicy: Never
        envFrom:
        - secretRef:
            name: superset-secrets
```

# Ход выполнения

Запускаем Kubernets:

<img width="953" height="419" alt="Снимок экрана 2026-03-22 230223" src="https://github.com/user-attachments/assets/a7350d0a-0a3f-4b62-8bf6-76ef45968a2d" />

Входим в окружение minikube и собираем образы.

Образ superset:

<img width="962" height="390" alt="Снимок экрана 2026-03-22 230715" src="https://github.com/user-attachments/assets/523c6554-4bf2-4bdd-85b9-be9a60253a86" />

Образ generator:

<img width="966" height="428" alt="Снимок экрана 2026-03-24 122313" src="https://github.com/user-attachments/assets/ca053dc3-a67d-40ac-bfe1-7b79aa8c83c2" />

Применим манифесты Kubernets:

<img width="570" height="192" alt="Снимок экрана 2026-03-22 231017" src="https://github.com/user-attachments/assets/62622f3a-1cac-4311-8d4d-258c9437dd60" />

Проверим доступность приложения:

<img width="950" height="129" alt="Снимок экрана 2026-03-24 000642" src="https://github.com/user-attachments/assets/0a92b525-3455-4544-8b38-f0ca4119a8e0" />

Superset успешно запустился, переходим в браузер:

<img width="1223" height="776" alt="Снимок экрана 2026-03-23 221056" src="https://github.com/user-attachments/assets/e73b5cbe-c4ec-4fac-b506-f8c6874dbb33" />

Заходим под admin admin:

<img width="1214" height="737" alt="Снимок экрана 2026-03-23 221117" src="https://github.com/user-attachments/assets/93aa8667-9bb9-4c17-8847-ccd4fd4b77aa" />

Подключаемся к базе данных:

<img width="1212" height="739" alt="Снимок экрана 2026-03-23 221236" src="https://github.com/user-attachments/assets/75e58601-1687-4dc4-8574-dbd66047f3b1" />

Подключение произошло успешно:

<img width="1211" height="356" alt="Снимок экрана 2026-03-23 221255" src="https://github.com/user-attachments/assets/9a0cad69-8909-4145-9960-266ba8c8af17" />

Добавляем наш датасет:

<img width="1215" height="733" alt="Снимок экрана 2026-03-23 221337" src="https://github.com/user-attachments/assets/42671a0e-f7c3-4450-ad87-23bb8eb7b9e7" />

Далее создаем графики и размещаем их на дашборде:

<img width="1209" height="682" alt="Снимок экрана 2026-03-24 000511" src="https://github.com/user-attachments/assets/18d81a7e-0693-4d56-bf0e-ba18f637f74d" />

##### Выводы по дашборду

###### Сезонность
В данных отсутствует ярко выраженная сезонность. Это характерно для магазина электроники, где спрос на товары распределен равномерно в течение года без значительных пиков в определенные периоды.

###### Региональное распределение
- **Москва** — данный филиал приносит наибольшую прибыль за счет более высокой плотности населения.
- **Новосибирск** — наименьшие показатели выручки, это может быть связано с меньшей численностью населения или более низкой покупательской активностью. Возможно, данный филиал открылся недавно.

###### Категории товаров
- **Смартфоны** — лидируют по объему продаж, так как часто меняются их модели. Эта категория товаров очень востребована.
- **Аксессуары** — занимают второе место, так как являются сопутствующими товарами, часто сменяемыми (например, чехлы для телефона) и недорогими.
- **Планшеты** — также показывают высокие показатели по объему продаж, пользуются стабильным спросом.
- **Электроника** — наименьшие продажи, ввиду более высокой стоимости и более длительного срока службы.

###### Типы клиентов
- **VIP-клиенты** — приносят наибольшую прибыль, вероятно в компании хорошо продуманные программы лояльности и индивидуальный подход.
- **Постоянные клиенты** — занимают промежуточное положение, приносят значительный вклад в выручку.
- **Новые клиенты** — показывают наименьшую прибыль, скорее всего компании стоит пересмотреть свои маркетинговые стратегии, чтобы привлекать больше новых клиентов.

Также добавим фильтры:

<img width="1193" height="685" alt="Снимок экрана 2026-03-24 000519" src="https://github.com/user-attachments/assets/20dd4880-67ee-4e7a-9b59-c34ea2452364" />

Попробуем их применить:

<img width="1220" height="694" alt="Снимок экрана 2026-03-24 000615" src="https://github.com/user-attachments/assets/6d6fa4ed-f2a1-4026-814b-131b3baf6dad" />

Теперь вернемся в терминал и проверим корректность работы всех подов:

<img width="951" height="124" alt="image" src="https://github.com/user-attachments/assets/72adc3ef-7d41-49d0-a618-0287e97129ab" />

Посмотрим сервисы:

<img width="759" height="110" alt="Снимок экрана 2026-03-24 000656" src="https://github.com/user-attachments/assets/16f949c4-09ce-4e4b-b0f0-728fdb942be1" />

И также проверим, что база данных действительно создалась и в нее были загружены все записи:

<img width="954" height="168" alt="Снимок экрана 2026-03-24 000710" src="https://github.com/user-attachments/assets/3a5d494d-0dbe-40df-be51-c784057835ec" />

Видим, что в таблице 1000 записей, как и должно быть

Теперь посмотрим первые 5 строк таблицы:

<img width="965" height="63" alt="Снимок экрана 2026-03-24 000719" src="https://github.com/user-attachments/assets/5462c533-86a0-4e04-8e69-5309dbe48590" />

<img width="989" height="502" alt="Снимок экрана 2026-03-24 000730" src="https://github.com/user-attachments/assets/bd96f610-8701-425b-b735-c611193d5fcc" />

# Вывод

В ходе выполнения лабораторной работы был полностью освоен процесс оркестрации контейнеров в Kubernetes. Успешно развёрнута связка из двух сервисов — Apache Superset и PostgreSQL. Отработаны механизмы управления масштабированием приложения с помощью Deployment, настроена сетевая доступность между компонентами с использованием различных типов Service. Все сервисы успешно взаимодействуют друг с другом, кластер функционирует стабильно. Поставленная цель достигнута.
