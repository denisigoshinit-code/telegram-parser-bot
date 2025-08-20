import requests
from bs4 import BeautifulSoup
import time
import csv

def get_avito_page_content(url):
    """
    Отправляет HTTP-запрос к сайту Avito и возвращает содержимое страницы.
    Добавляет задержку и заголовки для имитации браузера.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        time.sleep(1)
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к сайту: {e}")
        return None

def parse_avito_ads(soup):
    """
    Извлекает информацию об объявлениях из HTML-кода Avito.
    """
    ads = []
    
    # Ищем все родительские блоки объявлений по стабильному классу.
    # Эта та часть, которую мы нашли ранее.
    items = soup.find_all('div', class_='styles-item-uFKud')
    
    if not items:
        print("Не удалось найти элементы объявлений. Проверьте актуальность класса.")
        return []

    for item in items:
        try:
            # Ищем тег <a> внутри родительского блока.
            # Класс `styles-module-root-cfrVG` вы нашли сами!
            link_element = item.find('a', class_='styles-module-root-cfrVG')
            
            # Извлекаем название из атрибута `title` этого тега.
            title = link_element['title'] if link_element and 'title' in link_element.attrs else "Без названия"
            
            # Извлекаем ссылку из атрибута `href`.
            link = "https://www.avito.ru" + link_element['href'] if link_element and link_element.get('href') else "Без ссылки"
            
            # Ищем цену.
            # Мы используем класс `styles-module-size_xm-V3Vbt`, который вы также нашли.
            price_element = item.find('span', class_='styles-module-size_xm-V3Vbt')
            price = price_element.text.strip() if price_element else "Цена не указана"
            
            # Создаем словарь для удобного хранения данных.
            ad_data = {
                "title": title,
                "price": price,
                "link": link
            }
            ads.append(ad_data)
            
        except Exception as e:
            print(f"Ошибка при парсинге одного из объявлений: {e}")
            continue
            
    return ads

def save_to_csv(data, filename="avito_ads.csv"):
    """
    Сохраняет данные в CSV-файл.
    """
    if not data:
        print("Нет данных для сохранения.")
        return

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'price', 'link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(data)
        
    print(f"Данные успешно сохранены в файл {filename}")

if __name__ == "__main__":
    url = "https://www.avito.ru/all/bytovaya_elektronika"
    page_soup = get_avito_page_content(url)
    
    if page_soup:
        ad_list = parse_avito_ads(page_soup)
        if ad_list:
            print(f"Найдено {len(ad_list)} объявлений.")
            for ad in ad_list:
                print(ad)
            
            save_to_csv(ad_list)
        else:
            print("Объявления не найдены.")
    else:
        print("Не удалось получить содержимое страницы.")