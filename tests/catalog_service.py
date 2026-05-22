import requests


def _fetch_data(url: str):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_filtered_products(brand: str):
    data = _fetch_data('http://example.com/catalog')
    return [p for p in data.get('products', []) if p.get('brand') == brand]


def search_products(query: str):
    data = _fetch_data('http://example.com/catalog')
    return [p for p in data.get('products', []) if query.lower() in p.get('name', '').lower()]


def get_product_by_id(product_id: int):
    data = _fetch_data(f'http://example.com/catalog/{product_id}')
    return data


def get_similar_products(product_id: int):
    data = _fetch_data('http://example.com/catalog')
    target = next((p for p in data.get('products', []) if p.get('id') == product_id), None)
    if not target:
        return []
    category = target.get('category')
    return [p for p in data.get('products', []) if p.get('category') == category and p.get('id') != product_id]


def get_category_path(category_id: str):
    data = _fetch_data('http://example.com/categories')
    # Build simple path assuming single level with subs
    category_names = {
        "coffee-machines": "Кофемашины",
        "microwaves": "Микроволны",
    }
    for cat in data.get('categories', []):
        if category_id == cat.get('id'):
            return f"Главная > {cat.get('name')} > {category_names.get(category_id, category_id)}"
        if 'subs' in cat and category_id in cat['subs']:
            sub_name = category_names.get(category_id, category_id)
            return f"Главная > {cat.get('name')} > {sub_name}"
    return ''
