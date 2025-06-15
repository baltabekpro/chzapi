import os
import sys
import csv
import chardet
import pandas as pd
from datetime import datetime
from logger_config import get_logger, log_exception
from get_violations import PRODUCT_GROUPS

# Настройка логгера
logger = get_logger("reports_converter")

def detect_encoding(file_path):
    """
    Определяет кодировку бинарного файла
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(1024*1024)  # Читаем до 1MB для анализа
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
            confidence = result['confidence']
            logger.info(f"Обнаружена кодировка: {encoding} (достоверность: {confidence})")
            return encoding, confidence
    except Exception as e:
        logger.error(f"Ошибка при определении кодировки: {str(e)}")
        return 'utf-8', 0

def try_read_csv_with_encodings(file_path):
    """
    Пытается прочитать CSV-файл с различными кодировками и разделителями
    
    Returns:
        DataFrame или None в случае неудачи
    """
    encodings = ['cp1251', 'utf-8', 'utf-8-sig', 'windows-1251', 'latin1', 'iso-8859-1']
    separators = [';', ',', '\t', '|']
    
    # Добавляем обнаруженную кодировку в начало списка
    detected_encoding, confidence = detect_encoding(file_path)
    if detected_encoding and detected_encoding not in encodings:
        encodings.insert(0, detected_encoding)
        
    for encoding in encodings:
        for separator in separators:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=separator, error_bad_lines=False)
                if len(df.columns) > 1:  # Проверяем, что файл корректно разобран
                    logger.info(f"Успешно прочитан файл с кодировкой: {encoding}, разделитель: {separator}")
                    return df, encoding, separator
            except Exception as e:
                # Просто продолжаем с другими комбинациями
                pass
    
    # Если стандартные методы не сработали, пробуем прочитать как бинарный файл
    try:
        # Бинарное чтение и попытка декодирования
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Пробуем найти заголовок или структуру данных
        from io import BytesIO
        import struct
        
        # Проверяем наличие ZIP-сигнатуры
        if content.startswith(b'PK\x03\x04'):
            logger.info("Файл является ZIP-архивом")
            import zipfile
            with zipfile.ZipFile(BytesIO(content)) as zf:
                for name in zf.namelist():
                    if name.endswith('.csv'):
                        with zf.open(name) as csv_file:
                            csv_content = csv_file.read()
                            # Записываем извлеченный CSV во временный файл
                            temp_file = file_path + ".extracted.csv"
                            with open(temp_file, 'wb') as f:
                                f.write(csv_content)
                            logger.info(f"Извлечен CSV из ZIP: {name}, сохранен как {temp_file}")
                            # Рекурсивно вызываем для извлеченного файла
                            return try_read_csv_with_encodings(temp_file)
        
        logger.error(f"Не удалось прочитать файл: {file_path}")
        return None, None, None
        
    except Exception as e:
        logger.error(f"Ошибка при обработке бинарного файла: {str(e)}")
        return None, None, None

def convert_file(input_path, output_path):
    """
    Конвертирует CSV-файл в читаемый формат и сохраняет его
    
    Args:
        input_path: Путь к исходному файлу
        output_path: Путь для сохранения конвертированного файла
    
    Returns:
        True в случае успешной конвертации, иначе False
    """
    try:
        df, encoding, separator = try_read_csv_with_encodings(input_path)
        
        if df is None:
            logger.error(f"Не удалось прочитать файл: {input_path}")
            return False
        
        # Создаем директории, если их нет
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        # Сохраняем в читаемый формат
        df.to_csv(output_path, encoding='utf-8', index=False)
        
        # Также сохраняем в формате Excel для более удобного просмотра
        excel_path = output_path.replace('.csv', '.xlsx')
        df.to_excel(excel_path, index=False)
        
        logger.info(f"Файл успешно конвертирован: {input_path} -> {output_path}")
        logger.info(f"Также сохранен в Excel: {excel_path}")
        
        # Выводим статистику по группам товаров
        extract_product_group_info(input_path, df)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при конвертации файла {input_path}: {str(e)}")
        return False

def extract_product_group_info(file_path, df):
    """
    Извлекает информацию о товарной группе из имени файла и содержимого
    
    Args:
        file_path: Путь к файлу
        df: DataFrame с данными
    """
    try:
        import re
        # Извлекаем код группы из имени файла
        match = re.search(r'group(\d+)', os.path.basename(file_path))
        if match:
            group_code = int(match.group(1))
            group_name = PRODUCT_GROUPS.get(group_code, f"Неизвестная группа {group_code}")
            row_count = len(df)
            
            logger.info(f"Сводка по файлу {os.path.basename(file_path)}:")
            logger.info(f"Товарная группа: {group_name} (код {group_code})")
            logger.info(f"Количество записей: {row_count}")
            
            # Выводим первые столбцы для анализа
            if row_count > 0:
                columns = df.columns.tolist()
                logger.info(f"Столбцы: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
                
                # Пытаемся найти ключевые столбцы с данными о нарушениях
                key_columns = [col for col in columns if any(keyword in col.lower() for keyword in ['наруш', 'viol', 'дата', 'date', 'прич', 'cause'])]
                if key_columns:
                    logger.info(f"Ключевые столбцы: {', '.join(key_columns)}")
                    
                    # Выводим примеры первых строк для анализа
                    logger.info("Примеры первых записей:")
                    for idx, row in df.head(3).iterrows():
                        for col in key_columns:
                            value = str(row.get(col, ""))[:50]
                            if value and value.strip():
                                logger.info(f"  {col}: {value}{'...' if len(str(row.get(col, ''))) > 50 else ''}")
        else:
            logger.warning(f"Не удалось определить код товарной группы из имени файла: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка при извлечении информации о товарной группе: {str(e)}")

def process_all_reports(base_dir='output', output_dir='converted_reports'):
    """
    Обрабатывает все отчеты в директориях
    
    Args:
        base_dir: Базовая директория с отчетами
        output_dir: Директория для сохранения конвертированных отчетов
    """
    try:
        logger.info(f"Начинаем обработку отчетов из {base_dir}...")
        
        # Создаем директорию для конвертированных отчетов
        os.makedirs(output_dir, exist_ok=True)
        
        # Подсчет файлов
        total_files = 0
        converted_files = 0
        failed_files = 0
        
        # Получаем список всех директорий
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.lower().endswith('.csv'):
                    total_files += 1
                    input_path = os.path.join(root, file)
                    
                    # Создаем относительный путь для выходного файла
                    rel_path = os.path.relpath(root, base_dir)
                    output_path = os.path.join(output_dir, rel_path, f"readable_{file}")
                    
                    logger.info(f"Обработка файла: {input_path}")
                    
                    if convert_file(input_path, output_path):
                        converted_files += 1
                    else:
                        failed_files += 1
        
        logger.info(f"Обработка завершена. Всего файлов: {total_files}, успешно: {converted_files}, с ошибками: {failed_files}")
        
        # Выводим сводную информацию
        if converted_files > 0:
            logger.info(f"Конвертированные файлы доступны в директории: {os.path.abspath(output_dir)}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке отчетов: {str(e)}")

if __name__ == "__main__":
    try:
        # Проверяем наличие зависимостей
        try:
            import pandas
            import chardet
        except ImportError:
            import subprocess
            print("Установка необходимых зависимостей...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "chardet", "openpyxl"])
            print("Зависимости установлены.")
        
        # Получаем параметры из командной строки
        import argparse
        parser = argparse.ArgumentParser(description="Конвертер отчетов о нарушениях маркировки в читаемый формат")
        parser.add_argument('--input', '-i', default='output', 
                            help='Базовая директория с отчетами (по умолчанию: output)')
        parser.add_argument('--output', '-o', default='converted_reports',
                            help='Директория для сохранения конвертированных отчетов (по умолчанию: converted_reports)')
        parser.add_argument('--file', '-f', 
                            help='Обработать только указанный файл')
                            
        args = parser.parse_args()
        
        if args.file:
            # Обрабатываем только указанный файл
            if not os.path.exists(args.file):
                print(f"Ошибка: файл {args.file} не найден")
                sys.exit(1)
                
            output_path = os.path.join(args.output, f"readable_{os.path.basename(args.file)}")
            convert_file(args.file, output_path)
        else:
            # Обрабатываем все отчеты
            process_all_reports(args.input, args.output)
            
        print("Конвертация завершена успешно!")
        
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
