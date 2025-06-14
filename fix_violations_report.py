#!/usr/bin/env python3
"""
Скрипт для исправления проблемы одинаковых показателей в отчетах о нарушениях.
Запускает диагностику и применяет исправления.
"""

import os
import sys
import json
from datetime import datetime

def print_banner():
    banner = """
    =============================================
     ИСПРАВЛЕНИЕ ПРОБЛЕМЫ ОДИНАКОВЫХ ПОКАЗАТЕЛЕЙ
    =============================================
    
    Этот скрипт выполнит:
    1. Диагностику проблемы
    2. Исправление CSV-файлов
    3. Перегенерацию отчетов
    4. Валидацию результатов
    """
    print(banner)

def run_diagnostic():
    print("\nШаг 1. Запуск диагностики...\n")
    try:
        import diagnostic_violations
        diagnostic_violations.main()
        return True
    except Exception as e:
        print(f"Ошибка при выполнении диагностики: {e}")
        return False

def fix_csv_processing():
    print("\nШаг 2. Проверка и исправление файлов отчетов...\n")
    
    # Импортируем модуль для работы с отчетами
    try:
        from report_processor import validate_violation_counts
        print("Модуль report_processor успешно импортирован")
    except Exception as e:
        print(f"Ошибка при импорте модуля report_processor: {e}")
        return False
    
    # Поиск JSON-файлов с нарушениями
    import glob
    json_patterns = [
        'output/*/violations_*.json',
        'chz/output/*/violations_*.json',
        'main/output/*/violations_*.json'
    ]
    
    json_files = []
    for pattern in json_patterns:
        json_files.extend(glob.glob(pattern))
    
    print(f"Найдено JSON-файлов с отчетами о нарушениях: {len(json_files)}")
    if not json_files:
        print("Файлы отчетов не найдены")
        return False
    
    # Исправляем каждый JSON-файл
    fixed_files = 0
    for json_file in json_files:
        try:
            print(f"\nОбработка файла: {json_file}")
            
            # Читаем файл
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем наличие подозрительных данных
            violations = data.get('violations', {})
            if not violations:
                print("  Нет данных о нарушениях, пропуск")
                continue
            
            # Анализ повторяющихся значений
            values = list(violations.values())
            from collections import Counter
            value_counts = Counter(values)
            print("  Распределение значений:")
            for value, count in value_counts.items():
                print(f"    {value}: {count} раз")
            
            # Определяем, нужно ли исправить файл
            need_fix = False
            most_common = value_counts.most_common(1)
            if most_common:
                value, count = most_common[0]
                if count >= len(violations) * 0.5 and count > 3:
                    print(f"  Обнаружено подозрительное значение {value}, встречается {count} раз")
                    need_fix = True
            
            if need_fix:
                # Создаем резервную копию
                backup_file = f"{json_file}.bak"
                import shutil
                shutil.copy2(json_file, backup_file)
                print(f"  Создана резервная копия: {backup_file}")
                
                # Исправляем данные
                fixed_data = validate_violation_counts(data)
                
                # Сохраняем исправленный файл
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(fixed_data, f, ensure_ascii=False, indent=2)
                
                print("  Файл успешно исправлен")
                fixed_files += 1
            else:
                print("  Файл не требует исправления")
        
        except Exception as e:
            print(f"  Ошибка при обработке файла {json_file}: {e}")
    
    print(f"\nВсего исправлено файлов: {fixed_files} из {len(json_files)}")
    return fixed_files > 0

def regenerate_reports():
    print("\nШаг 3. Перегенерация отчетов...\n")
    
    # Запускаем процесс генерации и отправки отчетов
    try:
        # Импортируем необходимые модули
        from report_processor import process_and_send_all_reports
        result = process_and_send_all_reports()
        if result:
            print("Отчеты успешно перегенерированы и отправлены")
        else:
            print("Произошла ошибка при перегенерации отчетов")
        return result
    except Exception as e:
        print(f"Ошибка при перегенерации отчетов: {e}")
        return False

def validate_results():
    print("\nШаг 4. Проверка результатов...\n")
    
    # Поиск последних JSON-файлов с нарушениями
    import glob
    from datetime import datetime, timedelta
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    json_patterns = [
        f'output/*/violations_{yesterday}.json',
        f'chz/output/*/violations_{yesterday}.json',
        f'main/output/*/violations_{yesterday}.json'
    ]
    
    json_files = []
    for pattern in json_patterns:
        json_files.extend(glob.glob(pattern))
    
    print(f"Найдено JSON-файлов для проверки: {len(json_files)}")
    if not json_files:
        print("Файлы отчетов не найдены")
        return False
    
    # Проверяем каждый JSON-файл
    all_ok = True
    for json_file in json_files:
        try:
            print(f"\nПроверка файла: {json_file}")
            
            # Читаем файл
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем наличие данных о нарушениях
            violations = data.get('violations', {})
            if not violations:
                print("  Нет данных о нарушениях, пропуск")
                continue
            
            # Анализ повторяющихся значений
            values = list(violations.values())
            from collections import Counter
            value_counts = Counter(values)
            
            # Определяем, есть ли проблема с повторяющимися значениями
            problem = False
            most_common = value_counts.most_common(1)
            if most_common:
                value, count = most_common[0]
                if count >= len(violations) * 0.5 and count > 3:
                    print(f"  ПРОБЛЕМА: Значение {value} встречается {count} раз")
                    problem = True
            
            if not problem:
                print("  ✓ Файл проверен, проблем не обнаружено")
            else:
                print("  ✗ Файл содержит подозрительные данные")
                all_ok = False
        
        except Exception as e:
            print(f"  Ошибка при проверке файла {json_file}: {e}")
            all_ok = False
    
    return all_ok

def main():
    print_banner()
    
    # Подтверждение запуска
    if input("\nЗапустить процесс исправления? (y/n): ").lower() != 'y':
        print("Операция отменена")
        return
    
    # Шаг 1: Диагностика
    if not run_diagnostic():
        if input("\nПродолжить несмотря на ошибки диагностики? (y/n): ").lower() != 'y':
            print("Операция прервана")
            return
    
    # Шаг 2: Исправление данных
    if not fix_csv_processing():
        if input("\nПродолжить несмотря на ошибки исправления данных? (y/n): ").lower() != 'y':
            print("Операция прервана")
            return
    
    # Шаг 3: Перегенерация отчетов
    if not regenerate_reports():
        if input("\nПродолжить несмотря на ошибки перегенерации отчетов? (y/n): ").lower() != 'y':
            print("Операция прервана")
            return
    
    # Шаг 4: Проверка результатов
    results_ok = validate_results()
    
    # Вывод итогового сообщения
    if results_ok:
        print("\n✅ Проблема успешно исправлена!")
        print("Теперь отчеты содержат корректные данные о нарушениях товарных групп.")
    else:
        print("\n⚠️ Исправление выполнено, но обнаружены потенциальные проблемы.")
        print("Рекомендуется вручную проверить данные в отчетах.")
    
    print("\nПроцесс исправления завершен")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПроцесс прерван пользователем")
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
