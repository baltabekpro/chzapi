#!/usr/bin/env python
import os
import sys
import shutil

def switch_to_test_mode():
    """Переключиться в режим тестирования с одним сертификатом и одной группой"""
    print("Переключение в тестовый режим...")
    
    # Переключение cert_inns.json
    if os.path.exists("cert_inns.json.test"):
        if not os.path.exists("cert_inns.json.backup"):
            shutil.copy("cert_inns.json", "cert_inns.json.backup")
        shutil.copy("cert_inns.json.test", "cert_inns.json")
        print("- Файл cert_inns.json переключен в тестовый режим")
    else:
        print("! Файл cert_inns.json.test не найден")
    
    # Переключение get_violations.py
    if os.path.exists("get_violations.py.test"):
        if not os.path.exists("get_violations.py.backup"):
            shutil.copy("get_violations.py", "get_violations.py.backup")
        shutil.copy("get_violations.py.test", "get_violations.py")
        print("- Файл get_violations.py переключен в тестовый режим")
    else:
        print("! Файл get_violations.py.test не найден")
    
    # Переключение products.txt
    if not os.path.exists("products.txt.backup"):
        shutil.copy("products.txt", "products.txt.backup")
    
    # Создание тестового products.txt с одной группой
    with open("products.txt", 'w', encoding='utf-8') as f:
        f.write("8\n")  # Только молочные продукты
    print("- Файл products.txt переключен в тестовый режим (только группа 8)")
    
    # Переключение cert_thumbprints.txt
    if os.path.exists("cert_thumbprints.txt.test"):
        if not os.path.exists("cert_thumbprints.txt.backup"):
            shutil.copy("cert_thumbprints.txt", "cert_thumbprints.txt.backup")
        shutil.copy("cert_thumbprints.txt.test", "cert_thumbprints.txt")
        print("- Файл cert_thumbprints.txt переключен в тестовый режим")
    else:
        print("! Файл cert_thumbprints.txt.test не найден")
    print("Переключение в тестовый режим завершено.")

def switch_to_production_mode():
    """Вернуться к полному режиму с всеми сертификатами и группами"""
    print("Возврат к полному режиму...")
    
    # Возврат cert_inns.json
    if os.path.exists("cert_inns.json.backup"):
        shutil.copy("cert_inns.json.backup", "cert_inns.json")
        print("- Файл cert_inns.json восстановлен из резервной копии")
    else:
        print("! Файл cert_inns.json.backup не найден")
    
    # Возврат get_violations.py
    if os.path.exists("get_violations.py.backup"):
        shutil.copy("get_violations.py.backup", "get_violations.py")
        print("- Файл get_violations.py восстановлен из резервной копии")
    else:
        print("! Файл get_violations.py.backup не найден")
    
    # Возврат cert_thumbprints.txt
    if os.path.exists("cert_thumbprints.txt.backup"):
        shutil.copy("cert_thumbprints.txt.backup", "cert_thumbprints.txt")
        print("- Файл cert_thumbprints.txt восстановлен из резервной копии")
    else:
        print("! Файл cert_thumbprints.txt.backup не найден")
    
    print("Возврат к полному режиму завершен.")

if __name__ == "__main__":
    print("Утилита переключения между тестовым и полным режимом")
    print("1 - Переключиться в тестовый режим (1 сертификат, 1 группа)")
    print("2 - Вернуться к полному режиму")
    print("3 - Выйти без изменений")
    
    choice = input("Ваш выбор (1, 2 или 3): ")
    
    if choice == "1":
        switch_to_test_mode()
    elif choice == "2":
        switch_to_production_mode()
    elif choice == "3":
        print("Выход без изменений.")
        sys.exit(0)
    else:
        print("Неверный выбор. Введите 1, 2 или 3.")
        sys.exit(1)
