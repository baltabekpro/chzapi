"""
Расширенный скрипт для получения токена True API.
Поддерживает работу с сертификатами с указанием ИНН и ТС.
"""

import requests
import json
import sys
import base64
import os
import subprocess
from datetime import datetime
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# Базовый URL API
BASE_URL = "https://markirovka.crpt.ru/api/v3/true-api"
# BASE_URL = "https://markirovka.sandbox.crptech.ru/api/v3/true-api"  # Тестовый контур

def get_auth_data():
    """Получает данные для подписи от сервера авторизации"""
    try:
        response = requests.get(
            f"{BASE_URL}/auth/key",
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        data = response.json()
        return data['uuid'], data['data']
    except Exception as e:
        print(f"{Fore.RED}Ошибка при получении данных для аутентификации: {str(e)}")
        if hasattr(e, 'response'):
            print(f"{Fore.RED}Ответ сервера: {e.response.text}")
        sys.exit(1)

def save_data_to_sign(data_to_sign):
    """Сохраняет данные для подписи в файл"""
    try:
        with open('data_to_sign.txt', 'w', encoding='utf-8') as f:
            f.write(data_to_sign)
        print(f"\n{Fore.CYAN}Данные для подписи сохранены в файл: data_to_sign.txt")
    except Exception as e:
        print(f"{Fore.RED}Ошибка при сохранении данных для подписи: {e}")

def read_signature_file(file_path):
    """Читает файл подписи и кодирует его в base64"""
    try:
        with open(file_path, 'rb') as f:
            signature_data = f.read()
            # Пробуем определить, является ли данные уже в base64
            try:
                base64.b64decode(signature_data)
                # Если декодирование успешно, значит данные уже в base64
                return signature_data.decode('utf-8')
            except:
                # Если нет - кодируем
                return base64.b64encode(signature_data).decode('utf-8')
    except Exception as e:
        print(f"{Fore.RED}Ошибка при чтении файла подписи: {e}")
        return None

def sign_data_with_cryptcp(data_file, thumbprint=None, pin=None):
    """Подписывает данные с помощью CryptCP"""
    cryptcp_path = r"C:\Program Files\Crypto Pro\CSP\cryptcp.exe"
    output_file = "signature.sig"
    
    if not os.path.exists(cryptcp_path):
        print(f"{Fore.RED}Не найден CryptCP по пути: {cryptcp_path}")
        return None
        
    try:
        # Команда для подписи
        cmd = [
            cryptcp_path,
            "-sign",          # Команда подписи
            "-der",          # Формат DER
            "-thumbprint", thumbprint,  # Сертификат по отпечатку
            data_file,      # Входной файл
            output_file     # Выходной файл
        ]
        
        # Добавляем PIN если указан
        if pin:
            cmd.extend(["-pin", pin])
        
        # Выполняем команду
        print(f"\n{Fore.CYAN}Выполняется команда: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, encoding='cp866')
        
        if result.returncode == 0:
            # Проверяем что файл создан
            if os.path.exists(output_file):
                print(f"\n{Fore.GREEN}Файл успешно подписан")
                return output_file
            else:
                print(f"\n{Fore.RED}Файл подписи не создан")
                return None
        else:
            print(f"\n{Fore.RED}Ошибка при подписании:")
            print(f"{Fore.RED}Код возврата: {result.returncode}")
            if result.stdout: print(f"{Fore.RED}STDOUT: {result.stdout}")
            if result.stderr: print(f"{Fore.RED}STDERR: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}Ошибка при работе с CryptCP: {e}")
        if os.path.exists(output_file):
            os.remove(output_file)
        return None

def get_token(uuid, signed_data, inn=None, use_mchd=False):
    """
    Получает токен, отправляя подписанные данные.
    
    Args:
        uuid: UUID запроса авторизации
        signed_data: Подписанные данные
        inn: ИНН организации (опционально)
        use_mchd: Использовать параметр МЧДО
    """
    try:
        # Формируем базовый запрос
        request_data = {
            'uuid': uuid,
            'data': signed_data
        }
        
        # Добавляем ИНН, если он указан
        if inn:
            print(f"{Fore.CYAN}Используем ИНН: {inn}")
            request_data['inn'] = inn
            
        # Добавляем параметр МЧДО, если требуется
        if use_mchd:
            print(f"{Fore.CYAN}Используем МЧДО: {use_mchd}")
            request_data['mchd'] = use_mchd
        
        response = requests.post(
            f"{BASE_URL}/auth/simpleSignIn",
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            json=request_data,
            verify=True
        )
        
        print(f"\n{Fore.CYAN}Статус ответа: {response.status_code}")
        print(f"{Fore.CYAN}Заголовки ответа: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"{Fore.CYAN}Ответ сервера:", json.dumps(response_json, indent=2, ensure_ascii=False))
            
            # Обработка конкретных ошибок
            if response.status_code in [400, 403]:
                error_msg = response_json.get('error_message', '')
                print(f"{Fore.YELLOW}API вернул ошибку: {error_msg}")
                
                # Если ошибка связана с ИНН
                if "организацией выполняется авторизация" in error_msg and not inn:
                    print(f"{Fore.YELLOW}Для этого сертификата требуется указать ИНН")
                    return None, "require_inn"
                    
                # Если пользователь не найден
                if "Пользователь не найден" in error_msg:
                    print(f"{Fore.YELLOW}Пользователь не зарегистрирован в системе")
                    return None, "user_not_found"
                    
                # Другие виды ошибок
                return None, "api_error"
            
            if response.status_code == 200:
                token = response_json.get('token')
                if token:
                    return token, "success"
                else:
                    print(f"{Fore.YELLOW}Токен отсутствует в ответе")
                    return None, "no_token"
            else:
                print(f"{Fore.YELLOW}Ответ сервера не содержит токен. Статус: {response.status_code}")
                return None, "api_error"
                
        except:
            print(f"{Fore.YELLOW}Тело ответа не содержит JSON")
            return None, "parse_error"
        
    except Exception as e:
        print(f"{Fore.RED}Ошибка при получении токена: {str(e)}")
        return None, "exception"

def save_tokens_json(tokens):
    """Save tokens to JSON file"""
    try:
        # If file exists, try to merge with existing tokens
        existing_tokens = {}
        try:
            if os.path.exists('true_api_tokens.json'):
                with open('true_api_tokens.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_tokens = data.get('tokens', {})
        except:
            pass
            
        # Merge with new tokens
        existing_tokens.update(tokens)
        
        with open('true_api_tokens.json', 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "tokens": existing_tokens,
                    "generated_at": datetime.now().isoformat()
                }, 
                f, 
                indent=2,
                ensure_ascii=False
            )
        print(f"\n{Fore.GREEN}Токены успешно сохранены в true_api_tokens.json")
        return True
    except Exception as e:
        print(f"{Fore.RED}Ошибка при сохранении токенов: {e}")
        return False

def load_certificates():
    """Load certificates from certificates.json"""
    try:
        with open('certificates.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('certificates', [])
    except FileNotFoundError:
        print(f"{Fore.RED}Файл certificates.json не найден")
        return []
    except Exception as e:
        print(f"{Fore.RED}Ошибка при чтении файла certificates.json: {e}")
        return []

def load_certificate_inns():
    """Load certificate to INN mapping"""
    try:
        if not os.path.exists('cert_inns.json'):
            # Create empty file if it doesn't exist
            with open('cert_inns.json', 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}
            
        with open('cert_inns.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"{Fore.RED}Ошибка при загрузке ИНН сертификатов: {e}")
        return {}

def save_certificate_inns(cert_inns):
    """Save certificate INN mapping"""
    try:
        with open('cert_inns.json', 'w', encoding='utf-8') as f:
            json.dump(cert_inns, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"{Fore.RED}Ошибка при сохранении ИНН сертификатов: {e}")
        return False

def get_tokens():
    """Получает токены для всех сертификатов"""
    tokens = {}
    
    try:
        # Load certificates from certificates.json
        certificates = load_certificates()
        
        if not certificates:
            print(f"{Fore.RED}Не найдены сертификаты в файле certificates.json")
            return {}
        
        # Загружаем сохраненные ТС и ИНН для сертификатов
        cert_inns = load_certificate_inns()
        
        print(f"{Fore.CYAN}Найдено {len(certificates)} сертификатов")
        
        for cert in certificates:
            thumbprint = cert.get('thumbprint')
            name = cert.get('name', thumbprint)
            multi_inn = cert.get('multi_inn', False)
            
            if not thumbprint:
                print(f"{Fore.RED}Пропускаем сертификат без отпечатка: {name}")
                continue
                
            print(f"\n{Fore.CYAN}==========================================")
            print(f"{Fore.CYAN}Получение токена для: {name}")
            print(f"{Fore.CYAN}Отпечаток: {thumbprint}")
            print(f"{Fore.CYAN}Мультипользовательский: {'Да' if multi_inn else 'Нет'}")
            print(f"{Fore.CYAN}==========================================")
            
            # Проверяем, есть ли сохраненные ТС и ИНН для этого сертификата
            cert_key = name if name else thumbprint
            tc_inn_pairs = cert_inns.get(cert_key, [])
            
            if tc_inn_pairs:
                print(f"{Fore.CYAN}Найдены сохраненные пары ТС-ИНН:")
                for pair in tc_inn_pairs:
                    for tc, inn in pair.items():
                        print(f"{Fore.CYAN}  {tc}: {inn}")
            
            # Если имеются пары ТС-ИНН, обрабатываем каждую пару независимо от настройки multi_inn
            if tc_inn_pairs:
                # Обрабатываем каждую пару ТС-ИНН
                for pair in tc_inn_pairs:
                    for tc, inn in pair.items():
                        print(f"\n{Fore.CYAN}Получение токена для ТС {tc} с ИНН {inn}")
                        
                        # Получаем свежие данные для подписи для каждого запроса
                        uuid, data_to_sign = get_auth_data()
                        save_data_to_sign(data_to_sign)
                        
                        signature_path = sign_data_with_cryptcp("data_to_sign.txt", thumbprint)
                        if not signature_path:
                            print(f"{Fore.RED}Не удалось создать подпись для {tc}")
                            continue
                            
                        signed_data = read_signature_file(signature_path)
                        if not signed_data:
                            continue
                        
                        # Получаем токен для текущей пары ТС-ИНН
                        token, status = get_token(uuid, signed_data, inn=inn)
                        
                        # Если токен получен успешно
                        if token and status == "success":
                            print(f"{Fore.GREEN}Токен успешно получен для {name} - {tc}")
                            # Сохраняем токен с идентификатором ТС
                            token_key = f"{name} - {tc}"
                            tokens[token_key] = token
            else:
                # Если нет пар ТС-ИНН, пробуем без ИНН
                
                # Получаем данные для подписи
                uuid, data_to_sign = get_auth_data()
                save_data_to_sign(data_to_sign)
                
                signature_path = sign_data_with_cryptcp("data_to_sign.txt", thumbprint)
                if not signature_path:
                    print(f"{Fore.RED}Не удалось создать подпись")
                    continue
                    
                signed_data = read_signature_file(signature_path)
                if not signed_data:
                    continue
                
                token, status = get_token(uuid, signed_data)
                
                # Если требуется указать ИНН
                if status == "require_inn":
                    tc = input(f"{Fore.YELLOW}Введите ТС для сертификата {name}: ").strip()
                    inn = input(f"{Fore.YELLOW}Введите ИНН для ТС {tc}: ").strip()
                    
                    if tc and inn:
                        # Сохраняем пару ТС-ИНН для будущего использования
                        cert_inns[cert_key] = [{tc: inn}]
                        save_certificate_inns(cert_inns)
                        print(f"{Fore.GREEN}Пара ТС-ИНН сохранена")
                        
                        # Пробуем получить токен с ИНН
                        token, status = get_token(uuid, signed_data, inn=inn)
                        
                        if token and status == "success":
                            print(f"{Fore.GREEN}Токен успешно получен для {name} - {tc}")
                            token_key = f"{name} - {tc}"
                            tokens[token_key] = token
                elif status == "success" and token:
                    print(f"{Fore.GREEN}Токен успешно получен для {name}")
                    tokens[name] = token
        
        # Save all tokens to a single JSON file
        if tokens:
            save_tokens_json(tokens)
            print(f"{Fore.GREEN}Получено и сохранено {len(tokens)} токенов")
        else:
            print(f"{Fore.RED}Не удалось получить ни одного токена")
            
    except Exception as e:
        print(f"{Fore.RED}Ошибка при получении токенов: {e}")
    
    return tokens

if __name__ == "__main__":
    get_tokens()