import requests
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from token_utils import get_any_valid_token

PRODUCT_GROUPS = {
    1: "Предметы одежды, бельё постельное, столовое, туалетное и кухонное",
    2: "Обувные товары",
    3: "Табачная продукция",
    4: "Духи и туалетная вода",
    5: "Шины и покрышки пневматические резиновые новые",
    6: "Фотокамеры (кроме кинокамер), фотовспышки и лампы-вспышки",
    8: "Молочная продукция",
    9: "Велосипеды и велосипедные рамы",
    10: "Медицинские изделия",
    11: "Слабоалкогольные напитки",
    12: "Альтернативная табачная продукция",
    13: "Упакованная вода",
    14: "Товары из натурального меха",
    15: "Пиво, напитки, изготавливаемые на основе пива, слабоалкогольные напитки",
    16: "Никотиносодержащая продукция",
    17: "Биологически активные добавки к пище",
    19: "Антисептики и дезинфицирующие средства",
    20: "Корма для животных",
    21: "Морепродукты",
    22: "Безалкогольное пиво",
    23: "Соковая продукция и безалкогольные напитки",
    26: "Ветеринарные препараты",
    27: "Игры и игрушки для детей",
    28: "Радиоэлектронная продукция",
    31: "Титановая металлопродукция",
    32: "Консервированная продукция",
    33: "Растительные масла",
    34: "Оптоволокно и оптоволоконная продукция",
    35: "Парфюмерные и косметические средства и бытовая химия",
    36: "Печатная продукция",
    37: "Бакалейная продукция",
    38: "Фармацевтическое сырьё, лекарственные средства",
    39: "Строительные материалы",
    40: "Пиротехника и огнетушащее оборудование",
    41: "Отопительные приборы",
    42: "Кабельно-проводниковая продукция",
    43: "Моторные масла",
    44: "Полимерные трубы"
}

def validate_date(date_str: str) -> str:
    """
    Проверяет и форматирует дату в правильный формат YYYY-MM-DD
    
    Args:
        date_str: Строка с датой в любом разумном формате
    Returns:
        Отформатированная дата в формате YYYY-MM-DD
    """
    try:
        # Пытаемся распознать различные форматы дат
        for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%Y.%m.%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
                
        # Если предыдущие форматы не подошли, пробуем разобрать по компонентам
        parts = date_str.replace('.', '-').replace('/', '-').split('-')
        if len(parts) == 3:
            year = parts[0] if len(parts[0]) == 4 else parts[2]
            month = parts[1].zfill(2)
            day = parts[2].zfill(2) if len(parts[0]) == 4 else parts[0].zfill(2)
            return f"{year}-{month}-{day}"
            
        raise ValueError("Неверный формат даты")
    except Exception as e:
        raise ValueError(f"Ошибка в формате даты: {e}")

class ViolationsReport:
    def __init__(self, token: str, is_sandbox: bool = False):
        """
        Инициализация клиента для получения отчета о нарушениях
        
        Args:
            token: Токен авторизации
            is_sandbox: Использовать песочницу вместо боевого контура
        """
        self.base_url = "https://markirovka.sandbox.crptech.ru/api/v3/true-api" if is_sandbox else "https://markirovka.crpt.ru/api/v3/true-api"
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_first_violation_date(self, product_group_code: int) -> str:
        """
        Получает дату самого раннего нарушения для товарной группы
        """
        try:
            # Создаем запрос на получение первого нарушения
            response = requests.get(
                f"{self.base_url}/violations/first-date",
                headers=self.headers,
                params={
                    'productGroupCode': product_group_code
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, dict) and data.get('firstViolationDate'):
                first_date = data['firstViolationDate'].split('T')[0]
                print(f"Найдена первая дата нарушения: {first_date}")
                return first_date
            
            # Если дата не найдена, пробуем альтернативный метод
            alt_response = requests.get(
                f"{self.base_url}/violations",
                headers=self.headers,
                params={
                    'productGroupCode': product_group_code,
                    'limit': 1,
                    'orderBy': 'violationDate',
                    'order': 'ASC'
                }
            )
            alt_response.raise_for_status()
            alt_data = alt_response.json()
            
            if alt_data and isinstance(alt_data, list) and len(alt_data) > 0:
                first_date = alt_data[0].get('violationDate', '').split('T')[0]
                if first_date:
                    print(f"Найдена первая дата нарушения: {first_date}")
                    return first_date

            # Если не удалось получить дату, используем дату 3 года назад
            default_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d")
            print(f"Не удалось найти первую дату нарушения, используем: {default_date}")
            return default_date

        except Exception as e:
            print(f"Ошибка при получении первой даты нарушения: {e}")
            default_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d")
            print(f"Используем дату по умолчанию: {default_date}")
            return default_date

    def create_violations_task(
        self,
        start_date: str,
        end_date: str,
        product_group_code: int,
        violation_categories: List[int] = None,
        violation_kinds: List[int] = None,
        violation_results: List[int] = None,
        operation_types: List[int] = None,
        gtin: str = None
    ) -> Dict[str, Any]:
        """
        Создает задание на выгрузку отчета о нарушениях
        
        Args:
            start_date: Дата начала периода (YYYY-MM-DD)
            end_date: Дата окончания периода (YYYY-MM-DD)
            product_group_code: Код товарной группы
            violation_categories: Список кодов категорий нарушений
            violation_kinds: Список кодов видов нарушений
            violation_results: Список кодов результатов нарушений
            operation_types: Список типов операций
            gtin: GTIN товара (14 цифр)
        """
        try:
            # Форматируем и проверяем даты
            start_date = validate_date(start_date)
            end_date = validate_date(end_date)
            
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            delta = end - start
            
            if delta.days > 91:
                raise ValueError("Период не может быть больше 91 дня")
            if delta.days < 0:
                raise ValueError("Дата начала должна быть меньше даты окончания")
                
            print(f"\nИспользуемый период:")
            print(f"Начало:  {start_date}")
            print(f"Конец:   {end_date}")
            print(f"Длина:   {delta.days + 1} дней")
            
        except ValueError as e:
            print(f"Ошибка в датах: {e}")
            sys.exit(1)

        # Формируем параметры фильтрации
        params = {}
        if violation_categories:
            params["violationCategory"] = violation_categories
        if violation_kinds:
            params["violationKind"] = violation_kinds
        if violation_results:
            params["violationResult"] = violation_results
        if operation_types:
            params["operationType"] = operation_types
        if gtin:
            if not (len(gtin) == 14 and gtin.isdigit()):
                raise ValueError("GTIN должен содержать 14 цифр")
            params["gtin"] = gtin

        # Формируем тело запроса
        request_data = {
            "name": "VIOLATIONS",
            "dataStartDate": start_date,
            "dataEndDate": end_date,
            "format": "CSV",
            "periodicity": "SINGLE",
            "params": json.dumps(params),
            "productGroupCode": product_group_code
        }

        try:
            response = requests.post(
                f"{self.base_url}/dispenser/tasks",
                headers=self.headers,
                json=request_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при создании задания: {e}")
            if hasattr(e, 'response'):
                print(f"Ответ сервера: {e.response.text}")
            sys.exit(1)

def split_date_range(start_date: str, end_date: str, product_group_code: int, max_tasks: int = 10) -> List[tuple[str, str]]:
    """
    Разбивает большой временной период на интервалы
    
    Args:
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
        product_group_code: Код товарной группы
        max_tasks: Максимальное количество заданий
    Returns:
        Список кортежей (start_date, end_date)
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days + 1
        
        if total_days <= 0:
            return []
        
        intervals = []
        current_start = start
        
        while current_start < end:
            # Определяем конец текущего интервала (не более 90 дней)
            current_end = min(current_start + timedelta(days=89), end)  # 89 дней + текущий день = 90 дней
            
            intervals.append((
                current_start.strftime("%Y-%m-%d"),
                current_end.strftime("%Y-%m-%d")
            ))
            
            # Если достигли максимального количества интервалов, сохраняем оставшиеся даты
            if len(intervals) >= max_tasks:
                if current_end < end:
                    save_remaining_dates(
                        (current_end + timedelta(days=1)).strftime("%Y-%m-%d"),
                        end.strftime("%Y-%m-%d"),
                        product_group_code
                    )
                    print("\nОставшиеся даты сохранены для следующего запуска")
                break
                
            current_start = current_end + timedelta(days=1)
        
        return intervals

    except Exception as e:
        print(f"Ошибка при разбиении дат: {e}")
        return []

def save_task_ids(task_ids: List[str], filename: str = 'violation_task_ids.txt') -> None:
    """
    Сохраняет ID заданий в файл
    
    Args:
        task_ids: Список ID заданий
        filename: Имя файла для сохранения
    """
    with open(filename, 'w') as f:
        for task_id in task_ids:
            f.write(f"{task_id}\n")

def save_remaining_dates(start_date: str, end_date: str, product_group_code: int, filename: str = 'remaining_dates.txt') -> None:
    """
    Сохраняет оставшиеся даты для последующей обработки
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
        product_group_code: Код товарной группы
        filename: Имя файла для сохранения
    """
    try:
        with open(filename, 'w') as f:
            json.dump({
                'start_date': start_date,
                'end_date': end_date,
                'product_group_code': product_group_code,
                'product_group_name': PRODUCT_GROUPS.get(product_group_code, 'Неизвестная группа'),
                'saved_at': datetime.now().isoformat()
            }, f, indent=2)
        print(f"\nОставшиеся даты сохранены в файл {filename}:")
        print(f"Товарная группа: {PRODUCT_GROUPS.get(product_group_code)}")
        print(f"Период: с {start_date} по {end_date}")
    except Exception as e:
        print(f"Ошибка при сохранении оставшихся дат: {e}")

def load_remaining_dates(filename: str = 'remaining_dates.txt') -> tuple[str, str, int]:
    """
    Загружает оставшиеся даты из файла
    
    Returns:
        tuple[start_date, end_date, product_group_code]
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return (
                data['start_date'], 
                data['end_date'],
                data['product_group_code']
            )
    except FileNotFoundError:
        return None, None, None
    except Exception as e:
        print(f"Ошибка при загрузке оставшихся дат: {e}")
        return None, None, None

def save_task_ids(task_ids):
    """Save task IDs to a file"""
    try:
        with open('violation_task_ids.txt', 'w') as f:
            f.write('\n'.join(map(str, task_ids)))
    except Exception as e:
        print(f"Error saving task IDs: {e}")

def load_remaining_dates():
    """Load remaining dates from file"""
    try:
        with open('remaining_dates.txt', 'r') as f:
            lines = f.read().splitlines()
            if len(lines) >= 3:
                return lines[0], lines[1], int(lines[2])
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error loading remaining dates: {e}")
    return None, None, None

def main():
    try:
        # Загружаем токен
        token = get_any_valid_token()
        if not token:
            print("Не найден действующий токен. Запустите сначала get_token.py")
            sys.exit(1)
            
        client = ViolationsReport(token)
        print("\n=== Создание отчета о нарушениях ===")
        
        # Проверяем наличие сохраненных дат
        saved_start, saved_end, saved_product_code = load_remaining_dates()
        
        start_date = None
        end_date = None
        product_group_code = None
        
        if all([saved_start, saved_end, saved_product_code]):
            print("\nНайдены сохраненные данные:")
            print(f"Товарная группа: {PRODUCT_GROUPS.get(saved_product_code)}")
            print(f"Начало периода: {saved_start}")
            print(f"Конец периода: {saved_end}")
            
            choice = input("\nВыберите действие:\n"
                         "1. Продолжить с сохраненными данными\n"
                         "2. Ввести новые данные\n"
                         "Выбор: ").strip()
            
            if choice == '1':
                start_date = saved_start
                end_date = saved_end
                product_group_code = saved_product_code
                
                # Проверяем, остался ли период после сохраненной даты
                saved_end_date = datetime.strptime(saved_end, "%Y-%m-%d")
                today = datetime.now()
                
                if saved_end_date < today:
                    print("\nОбнаружен дополнительный период:")
                    next_start = (saved_end_date + timedelta(days=1)).strftime("%Y-%m-%d")
                    next_end = today.strftime("%Y-%m-%d")
                    print(f"с {next_start} по {next_end}")
                    
                    if input("Добавить этот период? (y/n): ").lower() == 'y':
                        start_date = next_start
                        end_date = next_end
                
                try:
                    os.remove('remaining_dates.txt')
                    print("Файл remaining_dates.txt удален")
                except:
                    pass

        # Если нет сохраненных дат или пользователь отказался их использовать
        if not all([start_date, end_date, product_group_code]):
            print("\nВведите новые данные:")
            
            # Получаем даты (сохраненные или новые)
            start_date = None
            end_date = None
            
            # Проверяем наличие сохраненных дат
            saved_start, saved_end = load_remaining_dates()
            if saved_start and saved_end:
                print("\nНайдены сохраненные даты:")
                print(f"Начало: {saved_start}")
                print(f"Конец:  {saved_end}")
                if input("Использовать эти даты? (y/n): ").lower() == 'y':
                    start_date = saved_start
                    end_date = saved_end
                    try:
                        os.remove('remaining_dates.txt')
                        print("Файл remaining_dates.txt удален")
                    except:
                        pass

            # Если нет сохраненных дат или пользователь отказался их использовать
            if not start_date or not end_date:
                print("\nВведите даты в любом формате (например: 2024-03-01)")
                print("Для выгрузки за все время введите 'all'")
                
                # Сначала получаем код товарной группы
                while True:
                    try:
                        print("\nДоступные товарные группы:")
                        for code, name in PRODUCT_GROUPS.items():
                            print(f"{code}: {name}")
                        
                        product_group_code = input("\nВведите код товарной группы: ").strip()
                        product_group_code = int(product_group_code)
                        
                        if product_group_code in PRODUCT_GROUPS:
                            print(f"Выбрана группа: {PRODUCT_GROUPS[product_group_code]}")
                            break
                        else:
                            print("Неверный код товарной группы. Выберите из списка.")
                    except ValueError:
                        print("Ошибка: введите числовой код")
                
                # Теперь получаем даты
                while True:
                    try:
                        start_date_input = input("\nВведите дату начала (или 'all'): ").strip()
                        if start_date_input.lower() == 'all':
                            # Получаем первую дату нарушения для выбранной товарной группы
                            first_violation_date = client.get_first_violation_date(product_group_code)
                            print(f"\nНайдена первая дата нарушения: {first_violation_date}")
                            start_date = first_violation_date
                        else:
                            start_date = validate_date(start_date_input)
                        break
                    except ValueError as e:
                        print(f"Ошибка: {e}")
                        print("Попробуйте еще раз")
                
                while True:
                    try:
                        end_date_input = input("Введите дату окончания (Enter для текущей даты): ").strip()
                        if not end_date_input:
                            end_date = datetime.now().strftime("%Y-%m-%d")
                        else:
                            end_date = validate_date(end_date_input)
                        break
                    except ValueError as e:
                        print(f"Ошибка: {e}")
                        print("Попробуйте еще раз")

            # Получаем код товарной группы
            while True:
                try:
                    print("\nДоступные товарные группы:")
                    for code, name in PRODUCT_GROUPS.items():
                        print(f"{code}: {name}")
                    
                    product_group_code = input("\nВведите код товарной группы: ").strip()
                    product_group_code = int(product_group_code)
                    
                    if product_group_code in PRODUCT_GROUPS:
                        print(f"Выбрана группа: {PRODUCT_GROUPS[product_group_code]}")
                        break
                    else:
                        print("Неверный код товарной группы. Выберите из списка.")
                except ValueError:
                    print("Ошибка: введите числовой код")
                    print("Попробуйте еще раз")

        # Разбиваем период на интервалы
        intervals = split_date_range(
            start_date=start_date,
            end_date=end_date,
            product_group_code=product_group_code
        )
        
        if not intervals:
            print("Ошибка: некорректный период дат")
            sys.exit(1)
        
        # Выводим информацию о разбиении
        print(f"\nБудет создано {len(intervals)} заданий:")
        for i, (start, end) in enumerate(intervals, 1):
            days = (datetime.strptime(end, '%Y-%m-%d') - datetime.strptime(start, '%Y-%m-%d')).days + 1
            print(f"Задание {i}: {start} - {end} ({days} дней)")
        
        if input("\nПродолжить? (y/n): ").lower() != 'y':
            print("Операция отменена")
            return

        task_ids = []
        remaining_intervals = []
        
        # Обрабатываем интервалы
        for i, (interval_start, interval_end) in enumerate(intervals, 1):
            print(f"\nСоздание задания {i} из {len(intervals)}")  # Fixed typo here
            print(f"Период: с {interval_start} по {interval_end}")
            
            try:
                result = client.create_violations_task(
                    start_date=interval_start,
                    end_date=interval_end,
                    product_group_code=product_group_code
                )
                
                task_id = result.get('id')
                if task_id:
                    task_ids.append(task_id)
                    print("Задание успешно создано")
                
            except Exception as e:
                print(f"Ошибка при создании задания: {e}")
                remaining_intervals = intervals[i:]
                break

        # Сохраняем результаты
        if task_ids:
            save_task_ids(task_ids)
            print(f"\nСохранено {len(task_ids)} ID заданий")
        
        if remaining_intervals:
            next_start = remaining_intervals[0][0]
            final_end = remaining_intervals[-1][1]
            save_remaining_dates(next_start, final_end, product_group_code)
            print("\nОставшиеся даты сохранены для следующего запуска")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        print("Подробности:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()