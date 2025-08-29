#!/usr/bin/env python3
"""
avito-scraper — Улучшенный парсер Авито с надежным извлечением цены и локации
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import os
import argparse
import re
from urllib.parse import quote, urljoin

# =============== КОНСТАНТЫ ===============
BASE_URL = "https://www.avito.ru"

# Словарь для преобразования русских названий регионов в URL
REGIONS = {
    "москва": "moskva",
    "санкт-петербург": "sankt-peterburg", 
    "екатеринбург": "ekaterinburg",
    "новосибирск": "novosibirsk",
    "казань": "kazan",
    "нур-султан": "nur-sultan",
    "минск": "minsk",
    "киев": "kiev",
}

# =============== ОСНОВНАЯ ЛОГИКА ===============
def get_avito_page_content(url):
    """
    Отправляет HTTP-запрос к сайту Avito и возвращает содержимое страницы.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.avito.ru/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        time.sleep(2)  # Увеличиваем задержку для избежания блокировки
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при запросе: {e}")
        return None

def safe_extract_text(element, default="Не указано"):
    """Безопасно извлекает текст из элемента."""
    if element and element.text.strip():
        return element.text.strip()
    return default

def parse_avito_ads(soup):
    """
    Извлекает информацию об объявлениях с множественными селекторами.
    """
    ads = []
    
    # Несколько вариантов поиска объявлений
    selectors = [
        'div[data-marker="item"]',
        'div.iva-item-root',
        'div.items-item',
        'div.js-item',
        'article'
    ]
    
    items = []
    for selector in selectors:
        found_items = soup.select(selector)
        if found_items:
            items = found_items
            print(f"✅ Найдено элементов с селектором '{selector}': {len(items)}")
            break
    
    if not items:
        print("⚠️ Не удалось найти элементы объявлений.")
        # Сохраним HTML для отладки
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print("⚠️ HTML страницы сохранен в debug_page.html для анализа")
        return []

    for item in items:
        try:
            # ===== ЗАГОЛОВОК И ССЫЛКА =====
            title = "Без названия"
            link = "Без ссылки"
            
            title_selectors = [
                'a[data-marker="item-title"]',
                'h3[itemprop="name"]',
                'a.iva-item-title',
                'h3.title',
                'a.link-link'
            ]
            
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    title = title_elem.get('title', '') or title_elem.text.strip()
                    href = title_elem.get('href', '')
                    if href:
                        link = urljoin(BASE_URL, href)
                    break
            
            # ===== ЦЕНА =====
            price = "Цена не указана"
            price_selectors = [
                'meta[itemprop="price"]',
                'span[data-marker="item-price"]',
                'div.iva-item-price',
                'span.price',
                'p.price',
                'div[data-marker="item-price"]'
            ]
            
            for selector in price_selectors:
                price_elem = item.select_one(selector)
                if price_elem:
                    # Пробуем получить content атрибут для meta тега
                    if price_elem.name == 'meta' and price_elem.get('content'):
                        price = price_elem['content']
                    else:
                        price = price_elem.text.strip()
                    break
            
            # Очищаем цену от лишних символов
            if price != "Цена не указана":
                price = re.sub(r'[^\d\s]', '', price).strip()
                price = re.sub(r'\s+', ' ', price)  # Убираем множественные пробелы
            
            # ===== ЛОКАЦИЯ =====
            location = "Не указано"
            location_selectors = [
                'div[data-marker="item-address"]',
                'span[data-marker="item-address"]',
                'div.geo-address',
                'span.address',
                'div.item-address',
                'span[class*="address"]'
            ]
            
            for selector in location_selectors:
                loc_elem = item.select_one(selector)
                if loc_elem:
                    location = loc_elem.text.strip()
                    break
            
            # ===== ДАТА ===== (дополнительно)
            date = "Не указано"
            date_selectors = [
                'div[data-marker="item-date"]',
                'span.date',
                'div.item-date'
            ]
            
            for selector in date_selectors:
                date_elem = item.select_one(selector)
                if date_elem:
                    date = date_elem.text.strip()
                    break
            
            # Экранирование для CSV
            title = title.replace(";", ",").replace("\n", " ").replace("\r", " ")
            location = location.replace(";", ",").replace("\n", " ").replace("\r", " ")
            
            ad_data = {
                "title": title,
                "price": price,
                "location": location,
                "date": date,
                "link": link
            }
            
            ads.append(ad_data)
            
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге объявления: {e}")
            continue
            
    return ads

def save_to_csv(data, filename="avito_ads.csv"):
    """
    Сохраняет данные в CSV-файл.
    """
    if not data:
        print("❌ Нет данных для сохранения.")
        return

    os.makedirs("data", exist_ok=True)
    filepath = f"data/{filename}"
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['title', 'price', 'location', 'date', 'link']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for ad in data:
                writer.writerow(ad)
                
        print(f"✅ Данные успешно сохранены в файл {filepath}")
        print(f"📊 Всего записей: {len(data)}")
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении CSV: {e}")

def main():
    parser = argparse.ArgumentParser(description='Парсер Авито — улучшенная версия')
    parser.add_argument('--query', required=True, help='Поисковый запрос, например: "ноутбуки"')
    parser.add_argument('--region', default='moskva', help='Регион (русское или английское название)')
    parser.add_argument('--min-price', type=int, help='Минимальная цена')
    parser.add_argument('--max-price', type=int, help='Максимальная цена')
    parser.add_argument('--max-pages', type=int, default=3, help='Максимум страниц (по умолчанию 3)')
    parser.add_argument('--debug', action='store_true', help='Сохранить HTML для отладки')

    args = parser.parse_args()

    # Автоматическое преобразование региона
    region_lower = args.region.strip().lower()
    final_region = REGIONS.get(region_lower, region_lower)

    print(f"🔍 Поиск: {args.query}")
    print(f"📍 Регион: {final_region}")
    print(f"📄 Страниц: {args.max_pages}")
    if args.min_price:
        print(f"💰 Минимальная цена: {args.min_price}")
    if args.max_price:
        print(f"💰 Максимальная цена: {args.max_price}")
    print("-" * 50)

    all_ads = []
    base_search_url = f"{BASE_URL}/{final_region}?q={quote(args.query)}"
    
    # Добавляем параметры цены
    if args.min_price:
        base_search_url += f"&pmin={args.min_price}"
    if args.max_price:
        base_search_url += f"&pmax={args.max_price}"

    for page in range(1, args.max_pages + 1):
        url = f"{base_search_url}&p={page}"
        print(f"🌐 Страница {page}: {url}")
        
        soup = get_avito_page_content(url)
        if not soup:
            if page == 1:
                print("❌ Не удалось получить первую страницу.")
                return
            print(f"⚠️ Пропускаем страницу {page}")
            continue

        if args.debug and page == 1:
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            print("⚠️ HTML сохранен в debug_page.html")

        ads = parse_avito_ads(soup)
        if not ads:
            print(f"⚠️ На странице {page} не найдено объявлений")
            if page == 1:
                print("ℹ️ Совет: проверьте правильность региона и запроса")
            break

        all_ads.extend(ads)
        print(f"✅ На странице {page}: {len(ads)} объявлений")

        # Проверка на последнюю страницу
        next_button = soup.find('a', {'data-marker': 'pagination-next'})
        if not next_button:
            print("🔚 Это последняя страница")
            break

        # Задержка между страницами
        time.sleep(1)

    # Сохраняем результаты
    if all_ads:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', args.query)[:30]
        filename = f"avito_{safe_query}_{final_region}_{timestamp}.csv"
        save_to_csv(all_ads, filename)
        
        # Выводим примеры данных
        print("\n📋 Примеры найденных объявлений:")
        for i, ad in enumerate(all_ads[:3], 1):
            print(f"{i}. {ad['title'][:50]}... - {ad['price']} - {ad['location']}")
    else:
        print("❌ Не найдено ни одного объявления")

if __name__ == "__main__":
    main()