import pytest
from app.api.v1.dependencies import get_cors_origins

# Test that CORS origins are split correctly

@staticmethod
def test_get_cors_origins():
    print("\n ===Тест:получение списка CORS-оригиналов ===")
    origins = get_cors_origins()
    print(f"Полученные origins: {origins}")
    assert isinstance(origins, list)
    assert "http://localhost:3000" in origins, "отсутствует https://localhost:3000" 
    assert "http://localhost:5173" in origins, "отсутствует https://localhost:5173"
    print("+Тест пройден: origins корректны и содержат нужные URL")
