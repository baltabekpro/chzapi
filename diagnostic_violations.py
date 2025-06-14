#!/usr/bin/env python3
"""
Диагностика нарушений: анализ причин одинаковых показателей в отчетах
"""

import json
import csv
import os
import glob
from collections import defaultdict, Counter
from datetime import datetime
import sys

def analyze_json_violations():
    """Анализ JSON-файлов с нарушениями"""
    print("=== АНАЛИЗ JSON-ФАЙЛОВ С НАРУШЕНИЯМИ ===\n")
    
    # Поиск JSON файлов
    json_patterns = [
        'output/*/violations_*.json',
        'chz/output/*/violations_*.json',
        'main/output/*/violations_*.json'
    ]
    
    all_files = []
    for pattern in json_patterns:
        all_files.extend(glob.glob(pattern))
    
    print(f"Найдено JSON-файлов: {len(all_files)}")
    
    # Анализ содержимого
    violations_counts = defaultdict(list)
    dates = set()
    regions = set()
    
    for file_path in all_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            date = data.get('date', 'unknown')
            dates.add(date)
            
            # Извлекаем регион из пути
            region = file_path.split('/')[-2] if '/' in file_path else 'unknown'
            regions.add(region)
            
            violations = data.get('violations', {})
            
            # Анализируем каждую товарную группу
            for product, count in violations.items():
                violations_counts[product].append(count)
                
            print(f"Файл: {file_path}")
            print(f"  Дата: {date}, Регион: {region}")
            print(f"  Товарных групп: {len(violations)}")
            for product, count in violations.items():
                print(f"    {product}: {count}")
            print()
            
        except Exception as e:
            print(f"Ошибка при чтении {file_path}: {e}")
    
    print(f"\nОбщая статистика:")
    print(f"Уникальных дат: {len(dates)} - {sorted(dates)}")
    print(f"Уникальных регионов: {len(regions)}")
    print(f"Товарных групп: {len(violations_counts)}")
    
    print(f"\nАнализ повторяющихся значений:")
    for product, counts in violations_counts.items():
        count_frequency = Counter(counts)
        print(f"\n{product}:")
        print(f"  Всего значений: {len(counts)}")
        print(f"  Уникальных значений: {len(count_frequency)}")
        print(f"  Распределение:")
        for count, freq in count_frequency.most_common():
            print(f"    {count}: встречается {freq} раз(а)")
    
    return violations_counts

def find_csv_files():
    """Поиск CSV-файлов с исходными данными"""
    print("\n=== ПОИСК CSV-ФАЙЛОВ ===\n")
    
    csv_patterns = [
        'output/*/*.csv',
        'chz/output/*/*.csv', 
        'main/output/*/*.csv',
        '*.csv',
        'reports/*/*.csv',
        'data/*/*.csv'
    ]
    
    all_csv_files = []
    for pattern in csv_patterns:
        found = glob.glob(pattern)
        all_csv_files.extend(found)
    
    print(f"Найдено CSV-файлов: {len(all_csv_files)}")
    
    if all_csv_files:
        for csv_file in all_csv_files:
            print(f"  {csv_file}")
            try:
                # Анализ содержимого CSV
                with open(csv_file, 'r', encoding='cp1251') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    print(f"    Строк: {len(rows)}")
                    if rows:
                        print(f"    Заголовок: {rows[0][:3]}...")  # Первые 3 колонки
                        data_rows = len(rows) - 1 if len(rows) > 1 else 0
                        print(f"    Строк данных: {data_rows}")
            except Exception as e:
                print(f"    Ошибка чтения: {e}")
            print()
    
    return all_csv_files

def analyze_task_files():
    """Анализ файлов с задачами"""
    print("\n=== АНАЛИЗ ФАЙЛОВ ЗАДАЧ ===\n")
    
    task_patterns = [
        'output/*/pending_tasks.txt',
        'chz/output/*/pending_tasks.txt',
        'main/output/*/pending_tasks.txt',
        'pending_tasks.txt'
    ]
    
    task_files = []
    for pattern in task_patterns:
        task_files.extend(glob.glob(pattern))
    
    print(f"Найдено файлов задач: {len(task_files)}")
    
    for task_file in task_files:
        print(f"\nФайл: {task_file}")
        try:
            with open(task_file, 'r') as f:
                lines = f.readlines()
            print(f"Задач: {len(lines)}")
            for i, line in enumerate(lines[:5]):  # Первые 5 задач
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    task_id, group_code = parts[0], parts[1]
                    print(f"  {i+1}. Task ID: {task_id}, Group: {group_code}")
            if len(lines) > 5:
                print(f"  ... и еще {len(lines)-5} задач")
        except Exception as e:
            print(f"Ошибка чтения: {e}")

def analyze_products_txt():
    """Анализ файла products.txt"""
    print("\n=== АНАЛИЗ PRODUCTS.TXT ===\n")
    
    products_files = ['products.txt', 'chz/products.txt', 'main/products.txt']
    
    for products_file in products_files:
        if os.path.exists(products_file):
            print(f"Файл: {products_file}")
            try:
                with open(products_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                print(f"Строк: {len(lines)}")
                print(f"Коды групп: {[line.strip() for line in lines if line.strip()]}")
            except Exception as e:
                print(f"Ошибка чтения: {e}")
            print()

def analyze_aggregation_logic():
    """Анализ логики агрегации"""
    print("\n=== АНАЛИЗ ЛОГИКИ АГРЕГАЦИИ ===\n")
    
    # Проверяем, какие агрегационные скрипты существуют
    agg_files = ['aggregate_violations.py', 'chz/aggregate_violations.py', 'main/aggregate_violations.py']
    
    for agg_file in agg_files:
        if os.path.exists(agg_file):
            print(f"Найден файл агрегации: {agg_file}")
    
    # Проверяем report_processor
    proc_files = ['report_processor.py', 'chz/report_processor.py', 'main/report_processor.py']
    
    for proc_file in proc_files:
        if os.path.exists(proc_file):
            print(f"Найден процессор отчетов: {proc_file}")

def check_api_responses():
    """Проверка, есть ли сохраненные ответы API"""
    print("\n=== ПРОВЕРКА ОТВЕТОВ API ===\n")
    
    # Поиск файлов с ответами API
    api_patterns = [
        'response_*.json',
        'output/*/response_*.json',
        'chz/output/*/response_*.json',
        'api_responses/*.json'
    ]
    
    api_files = []
    for pattern in api_patterns:
        api_files.extend(glob.glob(pattern))
    
    print(f"Найдено файлов ответов API: {len(api_files)}")
    
    if api_files:
        for api_file in api_files[:5]:  # Первые 5 файлов
            print(f"\nФайл: {api_file}")
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"  Тип: {type(data)}")
                if isinstance(data, dict):
                    print(f"  Ключи: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"  Элементов: {len(data)}")
                    if data and isinstance(data[0], dict):
                        print(f"  Ключи первого элемента: {list(data[0].keys())}")
                        
            except Exception as e:
                print(f"  Ошибка: {e}")

def generate_recommendation():
    """Генерация рекомендаций по исправлению"""
    print("\n" + "="*50)
    print("РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
    print("="*50)
    
    print("""
1. ПРОБЛЕМА: Одинаковые показатели нарушений для разных товарных групп

2. ВЕРОЯТНЫЕ ПРИЧИНЫ:
   a) Все CSV-файлы содержат одинаковое количество строк (тестовые данные)
   b) Функция read_csv_with_encoding просто считает строки, не анализируя содержимое
   c) API возвращает одинаковые данные для разных товарных групп
   d) Ошибка в логике агрегации данных

3. РЕКОМЕНДАЦИИ:
   a) Проверить содержимое CSV-файлов на предмет реальных данных
   b) Изменить логику обработки CSV для анализа содержимого, а не только подсчета строк
   c) Добавить валидацию ответов API
   d) Реализовать правильную агрегацию по товарным группам
   e) Добавить логирование для отслеживания источника данных

4. НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ:
   - Запустить этот скрипт для диагностики
   - Проверить несколько CSV-файлов вручную
   - Исправить функцию read_csv_with_encoding
   - Добавить валидацию данных
    """)

def main():
    print("ДИАГНОСТИКА ПРОБЛЕМЫ ОДИНАКОВЫХ ПОКАЗАТЕЛЕЙ НАРУШЕНИЙ")
    print("=" * 60)
    print(f"Дата/время: {datetime.now()}")
    print()
    
    # Выполняем все анализы
    violations_counts = analyze_json_violations()
    csv_files = find_csv_files()
    analyze_task_files()
    analyze_products_txt()
    analyze_aggregation_logic()
    check_api_responses()
    
    # Генерируем рекомендации
    generate_recommendation()
    
    # Сохраняем отчет
    report = {
        "timestamp": datetime.now().isoformat(),
        "violations_analysis": dict(violations_counts),
        "csv_files_found": csv_files,
        "recommendation": "Check CSV content and fix aggregation logic"
    }
    
    with open('diagnostic_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nДиагностический отчет сохранен в: diagnostic_report.json")

if __name__ == "__main__":
    main()
