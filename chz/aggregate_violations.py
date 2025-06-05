import json
import os
from collections import defaultdict
from typing import Dict, List, Any
from datetime import datetime

def aggregate_violations(json_files: List[str]) -> Dict[str, Any]:
    """
    Агрегирует данные о нарушениях по товарам, регионам и типам нарушений
    """
    aggregated_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for violation in data.get('violations', []):
                product_name = violation.get('Наименование товара', 'Неизвестный товар')
                region = violation.get('Регион', 'Неизвестный регион')
                violation_type = violation.get('Вид отклонения', 'Неизвестное нарушение')
                
                # Увеличиваем счетчик для данной комбинации
                aggregated_data[product_name][region][violation_type] += 1
                
        except Exception as e:
            print(f"Ошибка при обработке файла {json_file}: {e}")
            continue
    
    # Преобразуем defaultdict в обычный dict для JSON
    result = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "source_files": len(json_files),
        },
        "statistics": {
            product: {
                region: dict(violations)
                for region, violations in regions.items()
            }
            for product, regions in aggregated_data.items()
        }
    }
    
    return result

def analyze_violations(json_files: List[str]) -> Dict[str, Any]:
    """
    Анализирует данные о нарушениях и создает детальную статистику
    """
    # Статистика по типам нарушений
    violations_by_type = defaultdict(int)
    # Статистика по товарам
    violations_by_product = defaultdict(int)
    # Статистика по регионам
    violations_by_region = defaultdict(int)
    # Общая статистика
    total_violations = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for violation in data.get('violations', []):
                total_violations += 1
                
                # Собираем данные
                product = violation.get('Наименование товара', 'Неизвестный товар')
                region = violation.get('Регион', 'Неизвестный регион')
                violation_type = violation.get('Вид отклонения', 'Неизвестное нарушение')
                
                violations_by_type[violation_type] += 1
                violations_by_product[product] += 1
                violations_by_region[region] += 1
                
        except Exception as e:
            print(f"Ошибка при обработке файла {json_file}: {e}")
            continue
    
    # Формируем результат
    result = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "source_files": len(json_files),
            "total_violations": total_violations
        },
        "summary": {
            "violations_by_type": dict(sorted(
                violations_by_type.items(),
                key=lambda x: x[1],
                reverse=True
            )),
            "top_products": dict(sorted(
                violations_by_product.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),  # Топ-10 товаров
            "top_regions": dict(sorted(
                violations_by_region.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),  # Топ-10 регионов
        },
        "percentages": {
            "violations_distribution": {
                vtype: round(count / total_violations * 100, 2)
                for vtype, count in violations_by_type.items()
            }
        }
    }
    
    return result

def analyze_violations_by_product_and_region(json_files: List[str]) -> Dict[str, Any]:
    """
    Создает детальную статистику с разбивкой по товарам и регионам
    """
    # Структура для хранения данных по каждому товару и региону
    stats = defaultdict(lambda: defaultdict(lambda: {
        "total_violations": 0,
        "violation_types": defaultdict(int),
        "violation_percentages": defaultdict(float)
    }))
    
    total_violations = 0
    
    # Собираем данные
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for violation in data.get('violations', []):
                total_violations += 1
                
                # Извлекаем данные с учетом разных возможных названий полей
                product_group = (
                    violation.get('Товарная группа') or 
                    violation.get('Группа товаров') or 
                    violation.get('Product Group', '')
                )
                
                region = (
                    violation.get('Регион') or 
                    violation.get('Субъект РФ') or 
                    violation.get('Субъект') or
                    violation.get('Region', '')
                )
                
                violation_type = (
                    violation.get('Вид отклонения') or 
                    violation.get('Тип нарушения') or
                    violation.get('Violation Type', '')
                )
                
                if not all([product_group, region, violation_type]):
                    print(f"Пропущена запись из-за отсутствия данных: {violation}")
                    continue
                
                # Очищаем и нормализуем названия
                product_group = product_group.strip()
                region = region.strip()
                violation_type = violation_type.strip()
                
                # Обновляем статистику
                stats[product_group][region]['total_violations'] += 1
                stats[product_group][region]['violation_types'][violation_type] += 1
                
        except Exception as e:
            print(f"Ошибка при обработке файла {json_file}: {e}")
            continue
    
    # Формируем итоговый отчет
    result = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "source_files": len(json_files),
            "total_violations": total_violations,
            "unique_products": len(stats),
            "unique_regions": len(set(region for product in stats.values() for region in product))
        },
        "overall_statistics": {
            "total_violations": total_violations,
            "products_count": len(stats),
            "top_products": dict(sorted(
                {product: sum(region_stats['total_violations'] 
                            for region_stats in regions.values())
                 for product, regions in stats.items()}.items(),
                key=lambda x: x[1],
                reverse=True
            ))
        },
        "product_statistics": {}
    }
    
    # Обрабатываем статистику по каждому товару и региону
    for product, regions in stats.items():
        product_total = sum(region_stats['total_violations'] for region_stats in regions.values())
        
        result["product_statistics"][product] = {
            "summary": {
                "total_violations": product_total,
                "unique_regions": len(regions),
                "percentage_of_total": round(product_total / total_violations * 100, 2)
            },
            "regions": {}
        }
        
        # Статистика по каждому региону
        for region, region_stats in regions.items():
            region_total = region_stats['total_violations']
            
            # Вычисляем процентное соотношение для типов нарушений в регионе
            violation_percentages = {
                vtype: round(count / region_total * 100, 2)
                for vtype, count in region_stats['violation_types'].items()
            }
            
            result["product_statistics"][product]["regions"][region] = {
                "total_violations": region_total,
                "percentage_of_product": round(region_total / product_total * 100, 2),
                "percentage_of_total": round(region_total / total_violations * 100, 2),
                "violations": {
                    "by_type": dict(sorted(
                        region_stats['violation_types'].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )),
                    "type_percentages": violation_percentages
                }
            }
    
    return result

def main():
    # Создаем директории
    reports_dir = 'reports'
    json_dir = os.path.join(reports_dir, 'json')
    aggregated_dir = os.path.join(reports_dir, 'aggregated')
    os.makedirs(aggregated_dir, exist_ok=True)

    # Ищем JSON файлы
    json_files = []
    for root, _, files in os.walk(json_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))

    if not json_files:
        print("JSON файлы не найдены в директории reports/json")
        return

    print(f"Найдено {len(json_files)} JSON файлов")
    
    # Анализируем данные
    analysis = analyze_violations_by_product_and_region(json_files)
    
    # Сохраняем результат
    output_file = os.path.join(
        aggregated_dir, 
        f"violations_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\nПодробный анализ сохранен в: {output_file}")
    
    # Выводим краткую статистику
    print("\nОбщая статистика:")
    print(f"Всего нарушений: {analysis['meta']['total_violations']}")
    print(f"Уникальных товаров: {analysis['meta']['unique_products']}")
    print(f"Уникальных регионов: {analysis['meta']['unique_regions']}")
    
    print("\nТоп товаров по количеству нарушений:")
    for product, count in analysis['overall_statistics']['top_products'].items():
        print(f"- {product}: {count}")
        product_stats = analysis['product_statistics'][product]
        print("  Распределение по регионам:")
        for region, stats in product_stats['regions'].items():
            print(f"    {region}: {stats['total_violations']} "
                  f"({stats['percentage_of_product']}% от товара, "
                  f"{stats['percentage_of_total']}% от общего)")

if __name__ == "__main__":
    main()
