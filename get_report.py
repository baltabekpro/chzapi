import requests
import json
import sys
import time
from datetime import datetime
import os
from typing import List
from token_utils import get_any_valid_token

class ReportDownloader:
    def __init__(self, token: str, product_group_code: int, is_sandbox: bool = False):
        """
        Args:
            token: API token
            product_group_code: Product group code (e.g. 2 for shoes)
            is_sandbox: Use sandbox environment if True
        """
        self.base_url = "https://markirovka.sandbox.crptech.ru/api/v3/true-api" if is_sandbox else "https://markirovka.crpt.ru/api/v3/true-api"
        self.product_group_code = product_group_code
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

    def get_task_status(self, task_id: str) -> dict:
        """Получает статус задания"""
        try:
            response = requests.get(
                f"{self.base_url}/dispenser/tasks/{task_id}",
                headers=self.headers,
                params={'pg': self.product_group_code}  # Add product group code
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка при получении статуса задания: {e}")
            if hasattr(e, 'response'):
                print(f"Ответ сервера: {e.response.text}")
            sys.exit(1)

    def get_results_list(self, page: int = 0, size: int = 10, task_ids: List[str] = None) -> dict:
        """Получает список результатов выгрузок"""
        try:
            params = {
                'page': page,
                'size': size,
                'pg': self.product_group_code
            }
            
            if task_ids:
                params['task_ids'] = task_ids

            response = requests.get(
                f"{self.base_url}/dispenser/results",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка при получении списка результатов: {e}")
            if hasattr(e, 'response'):
                print(f"Ответ сервера: {e.response.text}")
            return None

    def download_result_file(self, result_id: str, output_dir: str) -> bool:
        """Скачивает файл результата выгрузки"""
        try:
            params = {'pg': self.product_group_code}

            # Get task info
            try:
                response = requests.get(
                    f"{self.base_url}/dispenser/results/{result_id}",
                    headers=self.headers,
                    params={'pg': self.product_group_code}
                )
                response.raise_for_status()
                task_info = response.json()
            except:
                print("Не удалось получить информацию о задании")
                task_info = None

            # Download file
            response = requests.get(
                f"{self.base_url}/dispenser/results/{result_id}/file",
                headers={**self.headers, 'Accept': '*/*'},
                params=params
            )
            
            # Если нет доступа к товарной группе, пропускаем задачу
            if response.status_code == 403:
                try:
                    err = response.json().get('error_message', response.text)
                except:
                    err = response.text
                print(f"Skip task {result_id}, no access: {err}")
                return True
     
            if response.status_code == 204:
                print("Файл пуст")
                return True

            response.raise_for_status()
            
            # Generate filename with all necessary info
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            date_info = ""
            if task_info and task_info.get('task'):
                start_date = task_info['task'].get('dataStartDate', '').split('T')[0]
                end_date = task_info['task'].get('dataEndDate', '').split('T')[0]
                if start_date and end_date:
                    date_info = f"{start_date}_to_{end_date}"

            filename = f"violations_group{self.product_group_code}_{date_info}_{timestamp}.csv"
            
            # Save file to specified output directory
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Файл сохранен: {filepath}")
            
            return True
            
        except Exception as e:
            print(f"Ошибка при скачивании файла: {e}")
            if hasattr(e, 'response'):
                print(f"Ответ сервера: {e.response.text}")
            return False

    def monitor_and_download(self, task_id: str, output_dir: str) -> bool:
        """Monitor task status and download when ready"""
        attempt = 0
        max_attempts = 60
        
        while attempt < max_attempts:
            results = self.get_results_list(task_ids=[task_id])
            if not results or not results.get('list'):
                print("No results data")
                time.sleep(20)  # Wait 20 seconds before next attempt
                attempt += 1
                continue

            result = results['list'][0]
            status = result.get('downloadStatus')
            print(f"Download status: {status}")
            
            if status == 'SUCCESS':
                print("Report ready, downloading...")
                return self.download_result_file(result['id'], output_dir)
            elif status == 'FAILED':
                error = result.get('errorMessage') or result.get('fullErrorMessage')
                print(f"Download error: {error}")
                return False
            
            print("Waiting 20 seconds before next check...")
            time.sleep(20)
            attempt += 1

        print("Maximum attempts reached")
        return False

def read_task_ids(filename: str = 'violation_task_ids.txt') -> List[str]:
    """
    Читает ID заданий из файла
    
    Args:
        filename: Имя файла с ID заданий
    Returns:
        Список ID заданий
    """
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Файл {filename} не найден. Сначала запустите get_violations.py")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла с ID заданий: {e}")
        sys.exit(1)

def update_task_ids(task_ids: List[str], filename: str = 'violation_task_ids.txt') -> None:
    """
    Обновляет файл с ID заданиями, удаляя выполненные задания
    
    Args:
        task_ids: Список оставшихся ID заданий
        filename: Имя файла для обновления
    """
    try:
        with open(filename, 'w') as f:
            for task_id in task_ids:
                f.write(f"{task_id}\n")
        print(f"Файл {filename} обновлен. Осталось {len(task_ids)} заданий")
    except Exception as e:
        print(f"Ошибка при обновлении файла с ID заданий: {e}")

def main():
    # Загружаем токен
    token = get_any_valid_token()
    if not token:
        print("Не найден действующий токен. Запустите сначала get_token.py")
        sys.exit(1)

    # Читаем ID заданий из файла
    task_ids = read_task_ids()
    print(f"\nНайдено {len(task_ids)} заданий для обработки")

    product_group_code = 2  # Code for shoes

    # Создаем клиент
    client = ReportDownloader(token, product_group_code)
    
    # Создаем копию списка для отслеживания необработанных ID
    remaining_tasks = task_ids.copy()
    
    for i, task_id in enumerate(task_ids, 1):
        print(f"\nОбработка задания {i} из {len(task_ids)}")
        print(f"ID задания: {task_id}")
        
        print(f"Мониторинг и скачивание результата для задачи {task_id}...")
        if client.monitor_and_download(task_id, output_dir=f"reports/group_{product_group_code}"):
            print("Задача успешно завершена")
            remaining_tasks.remove(task_id)
            update_task_ids(remaining_tasks)
        else:
            print("Не удалось получить результат")

if __name__ == "__main__":
    main()
