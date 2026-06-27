from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path


BASE_URL = 'https://yenitoptanci.com'
LIST_URL = f'{BASE_URL}/Product/ProductList'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': f'{BASE_URL}/dropshipping',
}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in {'p', 'li', 'br', 'tr'}:
            self.parts.append('\n')

    def get_text(self):
        text = ' '.join(self.parts)
        text = re.sub(r'\s+\n\s+', '\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return html.unescape(text).strip()


def strip_tags(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment or '')
    return parser.get_text()


def clean_text(value: str) -> str:
    value = html.unescape(value or '')
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def parse_int(value: str):
    if not value:
        return None
    digits = re.sub(r'[^0-9]', '', value)
    return int(digits) if digits else None


def request_text(url: str, data: dict | None = None, retries: int = 3) -> str:
    encoded = None
    headers = dict(HEADERS)
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
    req = urllib.request.Request(url, data=encoded, headers=headers)
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return response.read().decode('utf-8', errors='replace')
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f'İstek başarısız: {url} ({last_error})')


def fetch_list_page(page: int) -> str:
    payload = {
        'TagUrl': 'dropshipping',
        'page': page,
        'CategoryId': '',
        'brandId': '',
        'supplierId': '',
        'ProductSearchOrderByType': '',
        'orderType': '',
        'name': '',
    }
    raw = request_text(LIST_URL, payload)
    data = json.loads(raw)
    if not data.get('success'):
        raise RuntimeError(f'Liste sayfası başarısız: {page}')
    return data.get('responseText') or ''


def extract_max_page(list_html: str) -> int:
    pages = [int(match) for match in re.findall(r'[?&]page=([0-9]+)', list_html)]
    return max(pages) if pages else 1


def parse_list_products(list_html: str) -> list[dict]:
    cards = re.split(r'<div class="col-xl-3 col-md-3 col-sm-6\s+col-xs-6 infinite-item"', list_html)
    products = []
    for card in cards[1:]:
        href_match = re.search(r'<div class="tp-product-thumb.*?<a href="([^"]+)"', card, re.S)
        img_match = re.search(r'<img class="yt-product-img" src="([^"]+)" alt="([^"]*)"', card, re.S)
        id_match = re.search(r'data-product-id="([^"]+)"', card)
        category_match = re.search(r'<div class="tp-product-category">\s*<a[^>]*>(.*?)</a>', card, re.S)
        name_match = re.search(r'class="yt-product-name">\s*(.*?)\s*</a>', card, re.S)
        if not href_match or not name_match:
            continue
        detail_path = html.unescape(href_match.group(1))
        products.append({
            'source_product_id': id_match.group(1) if id_match else '',
            'name': clean_text(name_match.group(1)),
            'source_category': clean_text(category_match.group(1)) if category_match else '',
            'image_url': html.unescape(img_match.group(1)).replace('//', '/') if img_match else '',
            'source_url': urllib.parse.urljoin(BASE_URL, detail_path),
        })
        if products[-1]['image_url'].startswith('https:/') and not products[-1]['image_url'].startswith('https://'):
            products[-1]['image_url'] = products[-1]['image_url'].replace('https:/', 'https://', 1)
    return products


def parse_detail_page(product: dict) -> dict:
    text = request_text(product['source_url'])
    stock_match = re.search(r'Stok:\s*<b>(.*?)</b>', text, re.S | re.I)
    desc_match = re.search(r'<div class="product-desc">(.*?)</div>\s*<div class="seller-profile-box"', text, re.S)
    info_tables = re.findall(r'<table class="info-table">(.*?)</table>', text, re.S)
    crumbs = re.findall(r'<div class="breadcrumb__list.*?</div>', text, re.S)
    crumb_texts = re.findall(r'<span><a [^>]+>(.*?)</a></span>', crumbs[0], re.S) if crumbs else []
    price_match = re.search(r'\\"price\\":([0-9]+(?:\.[0-9]+)?)', text)
    value_match = re.search(r'\\"value\\":([0-9]+(?:\.[0-9]+)?)', text)
    brand_match = re.search(r'\\"item_brand\\":\\"(.*?)\\"', text)
    code_match = re.search(r'<tr><td>Ürün Kodu</td><td>(.*?)</td></tr>', text, re.S)
    gtin_match = re.search(r'<tr><td>Gtin</td><td>(.*?)</td></tr>', text, re.S)

    info_lines = []
    for table in info_tables:
        for key, value in re.findall(r'<tr><td>(.*?)</td><td>(.*?)</td></tr>', table, re.S):
            key_text = clean_text(key)
            value_text = clean_text(value)
            if key_text or value_text:
                info_lines.append(f'{key_text}: {value_text}')

    desc_html = desc_match.group(1) if desc_match else ''
    description = strip_tags(desc_html)
    feature_items = [clean_text(item) for item in re.findall(r'<li>(.*?)</li>', desc_html, re.S)]
    all_images = []
    for image_url in re.findall(r'<div class="swiper-slide">\s*<img src="([^"]+)"', text, re.S):
        image_url = html.unescape(image_url).replace('//', '/')
        if image_url.startswith('https:/') and not image_url.startswith('https://'):
            image_url = image_url.replace('https:/', 'https://', 1)
        if image_url not in all_images:
            all_images.append(image_url)

    return {
        **product,
        'price': float(price_match.group(1)) if price_match else (float(value_match.group(1)) if value_match else None),
        'stock': parse_int(stock_match.group(1)) if stock_match else None,
        'description': description,
        'features': '\n'.join(feature_items),
        'technical_info': '\n'.join(info_lines),
        'brand': html.unescape(brand_match.group(1)) if brand_match else '',
        'product_code': clean_text(code_match.group(1)) if code_match else '',
        'gtin': clean_text(gtin_match.group(1)) if gtin_match else '',
        'category_path': ' > '.join(clean_text(item) for item in crumb_texts[1:]),
        'all_image_urls': '\n'.join(all_images),
    }


def map_category(row: dict) -> str:
    blob = ' '.join([
        row.get('source_category', ''),
        row.get('category_path', ''),
        row.get('name', ''),
    ]).lower()
    rules = [
        ('Telefon & Telefon Aksesuarları', ['telefon', 'cep telefonu', 'şarj', 'sarj', 'kılıf', 'kilif', 'numaratör', 'numarator']),
        ('Oto Aksesuar', ['araba', 'araç', 'arac', 'otomotiv', 'motor yağ', 'motor yag', 'lastik', 'motosiklet']),
        ('Motosiklet Ekipmanları', ['motosiklet', 'kask']),
        ('Mutfak Eşyaları', ['mutfak', 'pişirme', 'pisirme', 'servis', 'fryer', 'barbekü', 'barbeku', 'tabak', 'bardak']),
        ('Aydınlatma', ['lamba', 'ışık', 'isik', 'led', 'aydınlatma', 'aydinlatma']),
        ('Ev Dekorasyonu', ['dekor', 'duvar', 'kapı süsü', 'kapi susu', 'folyo', 'süs', 'sus']),
        ('Kamp Malzemeleri', ['kamp', 'outdoor', 'piknik']),
        ('Fitness Ekipmanları', ['fitness', 'spor ekipman']),
        ('Spor Giyim', ['spor giyim']),
        ('Çanta & Aksesuar', ['çanta', 'canta', 'aksesuar', 'anahtarlık', 'anahtarlik']),
        ('Ayakkabı', ['ayakkabı', 'ayakkabi']),
        ('Kadın Giyim', ['kadın', 'kadin', 'abiye']),
        ('Erkek Giyim', ['erkek']),
        ('Parfüm', ['parfüm', 'parfum']),
        ('Cilt Bakımı', ['cilt', 'bakım', 'bakim']),
        ('Makyaj', ['makyaj']),
        ('Saç Bakımı', ['saç', 'sac', 'şampuan', 'sampuan']),
        ('Ev & Yaşam', ['banyo', 'hırdavat', 'hirdavat', 'yapı', 'yapi', 'temizlik', 'çamaşır', 'camasir', 'dolap', 'bebek']),
    ]
    for category, keywords in rules:
        if any(keyword in blob for keyword in keywords):
            return category
    return 'Ev & Yaşam'


def scrape(max_pages: int | None, max_details: int | None, workers: int) -> list[dict]:
    first = fetch_list_page(1)
    total_pages = extract_max_page(first)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    print(f'Liste sayfası: 1/{total_pages}')
    list_products = parse_list_products(first)
    for page in range(2, total_pages + 1):
        print(f'Liste sayfası: {page}/{total_pages}')
        list_products.extend(parse_list_products(fetch_list_page(page)))
        time.sleep(0.1)

    unique = {}
    for item in list_products:
        unique[item['source_url']] = item
    list_products = list(unique.values())
    if max_details:
        list_products = list_products[:max_details]
    print(f'Detay çekilecek ürün: {len(list_products)}')

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(parse_detail_page, product): product for product in list_products}
        for index, future in enumerate(as_completed(future_map), start=1):
            product = future_map[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    **product,
                    'price': None,
                    'stock': None,
                    'description': '',
                    'features': '',
                    'technical_info': '',
                    'brand': '',
                    'product_code': '',
                    'gtin': '',
                    'category_path': '',
                    'all_image_urls': product.get('image_url', ''),
                    'scrape_error': str(exc),
                }
            row['category'] = map_category(row)
            row['discount_price'] = ''
            row['is_active'] = 'Evet'
            row.setdefault('scrape_error', '')
            results.append(row)
            if index % 25 == 0 or index == len(list_products):
                print(f'Detay ilerleme: {index}/{len(list_products)}')
    results.sort(key=lambda item: (item.get('category') or '', item.get('name') or ''))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-pages', type=int)
    parser.add_argument('--max-details', type=int)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--json-out', required=True)
    parser.add_argument('--csv-out')
    args = parser.parse_args()

    rows = scrape(args.max_pages, args.max_details, args.workers)
    Path(args.json_out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.csv_out:
        fields = [
            'name', 'category', 'description', 'price', 'discount_price', 'stock', 'is_active',
            'image_url', 'source_category', 'features', 'technical_info', 'brand', 'product_code',
            'gtin', 'category_path', 'all_image_urls', 'source_url', 'source_product_id', 'scrape_error',
        ]
        with open(args.csv_out, 'w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    missing_price = sum(1 for row in rows if row.get('price') in (None, ''))
    missing_stock = sum(1 for row in rows if row.get('stock') in (None, ''))
    print(f'Tamamlandı. Ürün: {len(rows)}, eksik fiyat: {missing_price}, eksik stok: {missing_stock}')


if __name__ == '__main__':
    main()
