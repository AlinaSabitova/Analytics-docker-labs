#!/usr/bin/env python3

import sqlite3
import csv
import os
import sys
import time

# Конфигурация
DB_PATH = os.getenv("DB_PATH", "/app/data/hr.db")
CSV_PATH = os.getenv("CSV_PATH", "/app/data/hr_data.csv")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "30"))

# SQL для создания таблицы
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    position TEXT NOT NULL,
    experience REAL NOT NULL,
    salary INTEGER NOT NULL,
    performance REAL NOT NULL,
    satisfaction REAL NOT NULL,
    left TEXT NOT NULL
);
"""

def print_table(data, headers):
    """Вывод данных в виде таблицы"""
    if not data:
        print("Нет данных")
        return
    
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    print("+" + "+".join("-" * (w + 2) for w in col_widths) + "+")
    
    header_line = "|"
    for i, h in enumerate(headers):
        header_line += f" {h.center(col_widths[i])} |"
    print(header_line)
    
    print("+" + "+".join("-" * (w + 2) for w in col_widths) + "+")
    
    for row in data:
        data_line = "|"
        for i, val in enumerate(row):
            data_line += f" {str(val).ljust(col_widths[i])} |"
        print(data_line)
    
    print("+" + "+".join("-" * (w + 2) for w in col_widths) + "+")

def wait_for_csv():
    """Ожидание появления CSV файла"""
    for attempt in range(1, MAX_RETRIES + 1):
        if os.path.exists(CSV_PATH):
            return True
        print(f"Ожидание CSV... ({attempt}/{MAX_RETRIES})")
        time.sleep(2)
    return False

def load_data():
    if not wait_for_csv():
        print("CSV файл не найден")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(CREATE_TABLE)
    
    cursor.execute("DELETE FROM employees;")
    
    loaded = 0
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row['id']), row['name'], int(row['age']), row['gender'],
                row['position'], float(row['experience']), int(row['salary']),
                float(row['performance']), float(row['satisfaction']), row['left']
            ))
            loaded += 1
    
    conn.commit()
    print(f"Загружено {loaded} записей в таблицу employees")
    
    # Выполняем GROUP BY запрос и выводим в виде таблицы
    print("\n--- Аналитический отчет по удержанию сотрудников ---")
    cursor.execute("""
        SELECT 
            CASE left WHEN 'Нет' THEN 'Работает' ELSE 'Уволился' END as status,
            COUNT(*) as count,
            ROUND(AVG(salary), 0) as avg_salary,
            ROUND(AVG(satisfaction), 2) as avg_satisfaction
        FROM employees
        GROUP BY left
    """)
    
    results = cursor.fetchall()
    headers = ["Статус", "Количество", "Ср. зарплата", "Ср. удовлетворенность"]
    print_table(results, headers)
    
    conn.close()

if __name__ == "__main__":
    load_data()