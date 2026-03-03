#!/usr/bin/env python3
 
import csv
import random
import os
 
# Конфигурация
SEED = 42
NUM_EMPLOYEES = 5000
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hr_data.csv")
 
random.seed(SEED)
 
# Русские имена и фамилии
 
MALE_NAMES = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
    "Никита", "Иван", "Денис", "Егор", "Владимир",
    "Павел", "Роман", "Олег", "Тимур", "Артур"
]
 
FEMALE_NAMES = [
    "Анна", "Мария", "Елена", "Ольга", "Наталья",
    "Екатерина", "Анастасия", "Татьяна", "Юлия", "Ирина",
    "Дарья", "Светлана", "Виктория", "Ксения", "Полина",
    "Александра", "Валентина", "Надежда", "Людмила", "Галина"
]
 
LAST_NAMES = [
    "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов",
    "Васильев", "Попов", "Новиков", "Федоров", "Морозов",
    "Волков", "Алексеев", "Лебедев", "Семенов", "Егоров",
    "Павлов", "Козлов", "Степанов", "Николаев", "Орлов"
]
 
def get_female_last_name(last_name):
    """Преобразует фамилию в женскую форму"""
    if last_name.endswith("ов") or last_name.endswith("ев") or last_name.endswith("ин"):
        return last_name + "а"
    else:
        return last_name + "а"
 
# Должности
POSITIONS = [
    "Младший специалист",
    "Специалист",
    "Ведущий специалист",
    "Руководитель группы",
    "Начальник отдела",
    "Директор департамента"
]
 
# Соответствие стажа для должностей
POSITION_EXPERIENCE = {
    "Младший специалист": (0, 1),
    "Специалист": (1, 3),
    "Ведущий специалист": (3, 6),
    "Руководитель группы": (5, 8),
    "Начальник отдела": (7, 12),
    "Директор департамента": (10, 20)
}
 
# Генерируем имя
def generate_full_name(emp_id: int, gender: str) -> str:    
    if gender == "Мужчина":
        first_name = random.choice(MALE_NAMES)
        last_name = random.choice(LAST_NAMES)
        return f"{last_name} {first_name}"
    else:
        first_name = random.choice(FEMALE_NAMES)
        last_name = random.choice(LAST_NAMES)
        female_last_name = get_female_last_name(last_name)
        return f"{female_last_name} {first_name}"
 
# Генерируем одного сотрудника
def generate_employee(emp_id: int) -> dict:    
    # Пол (Мужчина/Женщина) 
    gender = random.choice(["Мужчина", "Женщина"])
    
    # Возраст от 21 до 65
    age = random.randint(21, 65)
    
    # Стаж (не может быть больше: возраст - 18)
    max_possible_experience = age - 18
    experience = random.randint(0, min(30, max_possible_experience))
    
    # Должность - зависит от стажа
    if experience < 1:
        position = "Младший специалист"
    elif experience < 3:
        position = random.choices(
            ["Младший специалист", "Специалист"],
            weights=[0.3, 0.7]
        )[0]
    elif experience < 6:
        position = random.choices(
            ["Специалист", "Ведущий специалист"],
            weights=[0.4, 0.6]
        )[0]
    elif experience < 8:
        position = random.choices(
            ["Ведущий специалист", "Руководитель группы"],
            weights=[0.5, 0.5]
        )[0]
    elif experience < 12:
        position = random.choices(
            ["Руководитель группы", "Начальник отдела"],
            weights=[0.4, 0.6]
        )[0]
    else:
        position = random.choices(
            ["Начальник отдела", "Директор департамента"],
            weights=[0.7, 0.3]
        )[0]
    
    # Зарплата 
    salary_by_position = {
        "Младший специалист": (60000, 80000),
        "Специалист": (80000, 120000),
        "Ведущий специалист": (120000, 180000),
        "Руководитель группы": (180000, 220000),
        "Начальник отдела": (220000, 300000),
        "Директор департамента": (300000, 400000)
    }
    
    min_sal, max_sal = salary_by_position[position]
    
    # Зарплата зависит от стажа
    exp_min, exp_max = POSITION_EXPERIENCE[position]
    if exp_max > exp_min:
        progress = min(1.0, (experience - exp_min) / (exp_max - exp_min))
    else:
        progress = 0.5
    
    salary = int(min_sal + (max_sal - min_sal) * progress * random.uniform(0.9, 1.1))
    
    # Производительность
    performance = round(random.gauss(3.5, 0.8), 1)
    performance = max(1.0, min(5.0, performance))
    
    # Удовлетворенность 
    salary_norm = (salary - min_sal) / (max_sal - min_sal) if max_sal > min_sal else 0.5
    
    satisfaction = 3.0 + salary_norm * 1.5 + (performance - 3.0) * 0.3
    
    satisfaction += random.gauss(0, 0.3)
    
    # Влияние стажа
    if experience < 1:
        satisfaction += 0.3  
    elif experience > 10:
        satisfaction -= 0.2 
    elif experience > 15:
        satisfaction -= 0.4 
    
    # Влияние возраста
    if age > 55:
        satisfaction -= 0.2
    elif age < 25:
        satisfaction += 0.2
    
    satisfaction = max(1.0, min(5.0, satisfaction))
    satisfaction = round(satisfaction, 1)
    
    # Вероятность увольнения 
    left_prob = 0.05 + (5.0 - satisfaction) * 0.1
    
    # Новые сотрудники увольняются чаще
    if experience < 1:
        left_prob += 0.15
    # Сотрудники со стажем 1-3 года тоже часто уходят
    elif 1 <= experience <= 3:
        left_prob += 0.1
    # Опытные сотрудники увольняются реже
    elif experience > 5:
        left_prob *= 0.7
    
    # Очень высокая удовлетворенность снижает вероятность
    if satisfaction > 4.0:
        left_prob *= 0.3
    # Очень низкая удовлетворенность повышает вероятность
    elif satisfaction < 2.0:
        left_prob *= 2.0
    
    # Ограничиваем вероятность
    left_prob = max(0.01, min(0.95, left_prob))
    
    # Факт увольнения
    left = 1 if random.random() < left_prob else 0
    
    # Генерируем полное имя
    full_name = generate_full_name(emp_id, gender)
    
    return {
        "id": emp_id,
        "name": full_name,
        "age": age,
        "gender": gender,
        "position": position,
        "experience": experience,
        "salary": salary,
        "performance": performance,
        "satisfaction": satisfaction,
        "left": "Да" if left == 1 else "Нет"
    }
 
def generate():
    """Основная функция генерации"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    employees = []
    for i in range(1, NUM_EMPLOYEES + 1):
        emp = generate_employee(i)
        employees.append(emp)
    
    # Сохраняем в CSV
    fieldnames = ["id", "name", "age", "gender", "position", 
                  "experience", "salary", "performance", 
                  "satisfaction", "left"]
    
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(employees)
    
    print(f"CSV файл успешно создан: {OUTPUT_FILE}")
    
if __name__ == "__main__":
    generate()