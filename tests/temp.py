
# Тест просмотра своих товаров

def test_view_my_products_success(jwt_token, requests_mock):
    # Мокаем GET запрос к эндпоинту просмотра товаров продавца
    requests_mock.get(
        f"{BASE_URL}/api/v1/seller/products",
        json=[
            {"id": "prod-1", "name": "Product A", "seller_id": 123},
            {"id": "prod-2", "name": "Product B", "seller_id": 123},
        ],
        status_code=200,
    )
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/seller/products", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for item in data:
        assert item["seller_id"] == 123
