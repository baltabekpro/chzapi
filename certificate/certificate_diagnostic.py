#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика сертификатов для поиска ошибок "товарная группа"
Автор: GitHub Copilot
Дата: 2025-06-05

Скрипт анализирует JWT токены и тестирует API вызовы для выявления
сертификатов, вызывающих ошибку "Текущий пользователь не принадлежит выбранной товарной группе"
"""

import csv
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import jwt
import requests

# Константы
PRODUCT_GROUPS = {
    1: "Предметы одежды",
    2: "Обувные товары",
    3: "Табачная продукция",
    4: "Духи и туалетная вода",
    5: "Шины и покрышки",
    6: "Фотокамеры",
    8: "Молочная продукция",
    9: "Велосипеды",
    10: "Медицинские изделия",
    11: "Слабоалкогольные напитки",
    12: "Альтернативная табачная продукция",
    13: "Упакованная вода",
    14: "Товары из натурального меха",
    15: "Пиво",
    22: "Безалкогольное пиво",
    23: "Соковая продукция",
    26: "Ветеринарные препараты",
    27: "Игры и игрушки",
    28: "Радиоэлектронная продукция",
    21: "Морепродукты",
    17: "БАДы",
    19: "Антисептики",
    35: "Парфюмерия и косметика",
    38: "Лекарственные средства",
}

BASE_URL = "https://markirovka.crpt.ru/api/v3/true-api"
TEST_DATE = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


class CertificateDiagnostic:
    """Основной класс для диагностики сертификатов"""

    def __init__(self, mode="safe"):
        """
        Инициализация диагностики
        mode: 'safe' - только анализ токенов, 'full' - с API тестами
        """
        self.mode = mode
        self.results = []
        self.tokens = []
        print(f"🔍 Диагностика сертификатов (режим: {mode})")
        print("=" * 60)

    def load_tokens(self) -> List[Tuple[str, str]]:
        """Загрузка токенов из файла"""
        try:
            with open("true_api_tokens.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                tokens = [(name, token) for name, token in data["tokens"].items()]
                print(f"📊 Загружено токенов: {len(tokens)}")
                self.tokens = tokens
                return tokens
        except Exception as e:
            print(f"❌ Ошибка загрузки токенов: {e}")
            return []

    def decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """Декодирование JWT токена"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            print(f"❌ Ошибка декодирования токена: {e}")
            return {}

    def get_token_info(self, token: str) -> Dict[str, Any]:
        """Извлечение информации из токена"""
        decoded = self.decode_jwt_token(token)
        if not decoded:
            return {}

        product_groups = decoded.get("product_group_info", [])
        return {
            "user": decoded.get("user", "Неизвестно"),
            "inn": decoded.get("inn", "Неизвестно"),
            "product_groups": product_groups,
            "active_groups": [g for g in product_groups if g.get("status") == "ACTIVE"],
            "inactive_groups": [
                g for g in product_groups if g.get("status") != "ACTIVE"
            ],
        }

    def map_group_name_to_code(self, group_name: str) -> int:
        """Сопоставление названия группы с кодом"""
        mapping = {
            "clothes": 1,
            "shoes": 2,
            "tobacco": 3,
            "perfumery": 4,
            "tires": 5,
            "photo": 6,
            "milk": 8,
            "bicycles": 9,
            "medical": 10,
            "lp": 11,
            "altTabacco": 12,
            "water": 13,
            "fur": 14,
            "beer": 15,
            "nabeer": 22,
            "softdrinks": 23,
            "vet": 26,
            "toys": 27,
            "radio": 28,
            "seafood": 21,
            "bio": 17,
            "antiseptic": 19,
            "chemistry": 35,
            "pharma": 38,
        }
        return mapping.get(group_name.lower())

    def analyze_token_access(self, cert_name: str, token: str) -> Dict[str, Any]:
        """Анализ доступа токена к товарным группам"""
        token_info = self.get_token_info(token)

        analysis = {
            "cert_name": cert_name,
            "user": token_info.get("user"),
            "inn": token_info.get("inn"),
            "total_groups": len(token_info.get("product_groups", [])),
            "active_groups": len(token_info.get("active_groups", [])),
            "inactive_groups": len(token_info.get("inactive_groups", [])),
            "group_access": {},
            "predictions": {},
        }

        # Анализируем доступ к каждой товарной группе
        for group_code, group_name in PRODUCT_GROUPS.items():
            has_access = False
            group_status = "NOT_FOUND"

            for group in token_info.get("product_groups", []):
                mapped_code = self.map_group_name_to_code(group.get("name", ""))
                if mapped_code == group_code:
                    has_access = True
                    group_status = group.get("status", "UNKNOWN")
                    break

            analysis["group_access"][group_code] = {
                "name": group_name,
                "has_access": has_access,
                "status": group_status,
            }

            # Прогноз успешности API вызова
            if has_access and group_status == "ACTIVE":
                analysis["predictions"][group_code] = "SUCCESS"
            elif has_access and group_status != "ACTIVE":
                analysis["predictions"][group_code] = "FAIL_INACTIVE"
            else:
                analysis["predictions"][group_code] = "FAIL_NO_ACCESS"

        return analysis

    def test_api_call(
        self, cert_name: str, token: str, product_group_code: int
    ) -> Dict[str, Any]:
        """Тестирование реального API вызова"""
        result = {
            "cert_name": cert_name,
            "product_group_code": product_group_code,
            "success": False,
            "error": None,
            "response_code": None,
            "task_id": None,
            "contains_товарная_группа_error": False,
        }

        try:
            url = f"{BASE_URL}/dispenser/tasks"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            payload = {
                "startDate": TEST_DATE,
                "endDate": TEST_DATE,
                "productGroupCode": product_group_code,
                "violationCategoryFilter": ["UNREGISTERED"],
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result["response_code"] = response.status_code

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("id"):
                    result["success"] = True
                    result["task_id"] = response_data["id"]
                else:
                    result["error"] = "No task ID in response"
            else:
                result["error"] = response.text
                # Проверяем на ошибку товарной группы
                if any(
                    phrase in response.text.lower()
                    for phrase in ["товарная группа", "товарной группе"]
                ):
                    result["contains_товарная_группа_error"] = True

        except Exception as e:
            result["error"] = str(e)

        return result

    def run_safe_analysis(self):
        """Безопасный анализ без API вызовов"""
        print("🛡️ Запуск безопасного анализа токенов...")

        tokens = self.load_tokens()
        if not tokens:
            return

        analysis_results = []
        problem_certificates = []

        for cert_name, token in tokens:
            print(f"\n🔑 Анализ: {cert_name}")

            analysis = self.analyze_token_access(cert_name, token)
            analysis_results.append(analysis)

            # Выводим краткую информацию
            print(f"   Пользователь: {analysis['user']}")
            print(f"   ИНН: {analysis['inn']}")
            print(f"   Групп всего: {analysis['total_groups']}")
            print(f"   Активных: {analysis['active_groups']}")
            print(f"   Неактивных: {analysis['inactive_groups']}")

            # Подсчитываем прогнозы
            predictions = analysis["predictions"]
            success_count = len([p for p in predictions.values() if p == "SUCCESS"])
            fail_count = len(predictions) - success_count

            print(f"   Прогноз: ✅ {success_count} успешных, ❌ {fail_count} неудачных")

            if analysis["inactive_groups"] > 0 or analysis["total_groups"] == 0:
                problem_certificates.append(cert_name)

        # Сохраняем результаты
        self.save_safe_analysis_results(analysis_results, problem_certificates)

        # Выводим итоги
        print("\n" + "=" * 60)
        print("📋 ИТОГИ БЕЗОПАСНОГО АНАЛИЗА")
        print("=" * 60)

        if problem_certificates:
            print("🚨 ПРОБЛЕМНЫЕ СЕРТИФИКАТЫ:")
            for cert in problem_certificates:
                print(f"   ❌ {cert}")
        else:
            print("✅ Критических проблем не обнаружено")

        print(f"\n💾 Результаты сохранены в файлы:")
        print(f"   - safe_analysis_summary.json")
        print(f"   - safe_analysis_predictions.csv")

    def run_full_diagnostic(self):
        """Полная диагностика с API тестами"""
        print("⚠️ Запуск полной диагностики с API вызовами!")
        print("Это создаст реальные задачи в системе ЦРПТ!")

        # Подтверждение
        response = input("\nПродолжить? (y/N): ").strip().lower()
        if response not in ["y", "yes", "да"]:
            print("❌ Диагностика отменена")
            return

        tokens = self.load_tokens()
        if not tokens:
            return

        all_results = []
        товарная_группа_errors = []

        total_tests = len(tokens) * len(PRODUCT_GROUPS)
        current_test = 0

        print(f"\n🚀 Начинаем тестирование {total_tests} комбинаций...")

        for cert_name, token in tokens:
            print(f"\n🔑 Тестирование: {cert_name}")

            for group_code, group_name in PRODUCT_GROUPS.items():
                current_test += 1
                progress = (current_test / total_tests) * 100

                print(
                    f"   [{current_test}/{total_tests}] ({progress:.1f}%) {group_name}...",
                    end=" ",
                )

                # Тестируем API вызов
                api_result = self.test_api_call(cert_name, token, group_code)
                all_results.append(api_result)

                if api_result["success"]:
                    print("✅")
                elif api_result["contains_товарная_группа_error"]:
                    print("❌ ТОВАРНАЯ ГРУППА")
                    товарная_группа_errors.append(
                        (cert_name, group_code, api_result["error"])
                    )
                else:
                    print(f"❌ {api_result['response_code']}")

                # Задержка между запросами
                time.sleep(0.5)

        # Сохраняем результаты
        self.save_full_diagnostic_results(all_results, товарная_группа_errors)

        # Выводим итоги
        print("\n" + "=" * 60)
        print("📋 ИТОГИ ПОЛНОЙ ДИАГНОСТИКИ")
        print("=" * 60)

        successful = len([r for r in all_results if r["success"]])
        failed = len(all_results) - successful
        товарная_группа_count = len(товарная_группа_errors)

        print(f"🔢 Всего тестов: {len(all_results)}")
        print(f"✅ Успешных: {successful}")
        print(f"❌ Неудачных: {failed}")
        print(f"🚫 Ошибок 'товарная группа': {товарная_группа_count}")

        if товарная_группа_errors:
            print(f"\n🔍 СЕРТИФИКАТЫ С ОШИБКАМИ 'ТОВАРНАЯ ГРУППА':")
            for cert, group, error in товарная_группа_errors[
                :10
            ]:  # Показываем первые 10
                print(f"   ❌ {cert} → Группа {group}")

        print(f"\n💾 Результаты сохранены в файлы:")
        print(f"   - full_diagnostic_summary.json")
        print(f"   - full_diagnostic_report.csv")

    def save_safe_analysis_results(
        self, analysis_results: List[Dict], problem_certificates: List[str]
    ):
        """Сохранение результатов безопасного анализа"""

        # JSON отчет
        summary = {
            "analysis_date": datetime.now().isoformat(),
            "mode": "safe",
            "total_certificates": len(analysis_results),
            "problem_certificates": problem_certificates,
            "detailed_analysis": analysis_results,
        }

        with open("safe_analysis_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # CSV для прогнозов
        with open(
            "safe_analysis_predictions.csv", "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Сертификат",
                    "Код_группы",
                    "Название_группы",
                    "Прогноз",
                    "Статус_в_токене",
                ]
            )

            for analysis in analysis_results:
                cert_name = analysis["cert_name"]
                for group_code, prediction in analysis["predictions"].items():
                    group_info = analysis["group_access"][group_code]
                    writer.writerow(
                        [
                            cert_name,
                            group_code,
                            group_info["name"],
                            prediction,
                            group_info["status"]
                            if group_info["has_access"]
                            else "NO_ACCESS",
                        ]
                    )

    def save_full_diagnostic_results(
        self, all_results: List[Dict], товарная_группа_errors: List[Tuple]
    ):
        """Сохранение результатов полной диагностики"""

        # JSON отчет
        summary = {
            "analysis_date": datetime.now().isoformat(),
            "mode": "full",
            "test_date": TEST_DATE,
            "total_tests": len(all_results),
            "successful_tests": len([r for r in all_results if r["success"]]),
            "failed_tests": len([r for r in all_results if not r["success"]]),
            "товарная_группа_errors": len(товарная_группа_errors),
            "detailed_results": all_results,
            "товарная_группа_error_details": [
                {
                    "certificate": cert,
                    "product_group_code": group,
                    "product_group_name": PRODUCT_GROUPS.get(group, "Unknown"),
                    "error": error,
                }
                for cert, group, error in товарная_группа_errors
            ],
        }

        with open("full_diagnostic_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # CSV отчет
        with open("full_diagnostic_report.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Сертификат",
                    "Код_группы",
                    "Название_группы",
                    "Успех",
                    "Код_ответа",
                    "ID_задачи",
                    "Ошибка_товарной_группы",
                    "Ошибка",
                ]
            )

            for result in all_results:
                group_name = PRODUCT_GROUPS.get(result["product_group_code"], "Unknown")
                writer.writerow(
                    [
                        result["cert_name"],
                        result["product_group_code"],
                        group_name,
                        "ДА" if result["success"] else "НЕТ",
                        result["response_code"] or "",
                        result["task_id"] or "",
                        "ДА" if result["contains_товарная_группа_error"] else "НЕТ",
                        result["error"] or "",
                    ]
                )


def main():
    """Основная функция"""
    print("🔍 ДИАГНОСТИКА СЕРТИФИКАТОВ")
    print(
        "Поиск ошибок 'Текущий пользователь не принадлежит выбранной товарной группе'"
    )
    print("=" * 70)

    # Проверяем наличие файла токенов
    if not os.path.exists("true_api_tokens.json"):
        print("❌ Файл true_api_tokens.json не найден!")
        print("Убедитесь, что файл находится в текущей директории.")
        return

    print("Выберите режим диагностики:")
    print("1. Безопасный анализ (только анализ токенов, без API вызовов)")
    print("2. Полная диагностика (с реальными API тестами)")
    print()

    choice = input("Введите номер режима (1 или 2): ").strip()

    if choice == "1":
        diagnostic = CertificateDiagnostic(mode="safe")
        diagnostic.run_safe_analysis()
    elif choice == "2":
        diagnostic = CertificateDiagnostic(mode="full")
        diagnostic.run_full_diagnostic()
    else:
        print("❌ Неверный выбор. Используйте 1 или 2.")


if __name__ == "__main__":
    main()
