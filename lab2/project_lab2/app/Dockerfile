# 1. Конкретная версия slim-образа (не latest)
FROM python:3.10-slim

# 2. Метаданные
LABEL maintainer="student" \
      description="HR Retention Analytics: ETL loader to SQLite + dashboard"

# 3. Установка системных зависимостей + SQLite утилиты + очистка кэша в одном слое
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        sqlite3 \
        sqlitebrowser \
        && \
    rm -rf /var/lib/apt/lists/*

# 4. Создание непривилегированного пользователя (UID 1000)
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 -m appuser

# 5. Рабочая директория
WORKDIR /app

# 6. Копирование и установка зависимостей ДО кода (кэш слоёв)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Копирование кода приложения
COPY loader.py dashboard.py ./

# 8. Переключение на непривилегированного пользователя
USER appuser

# 9. Порт Streamlit
EXPOSE 8501

# 10. Точка входа по умолчанию — дашборд
CMD ["streamlit", "run", "dashboard.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]