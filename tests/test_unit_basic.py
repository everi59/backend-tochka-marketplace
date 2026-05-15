import pytest
from app.infrastructure.config.config import Settings, get_settings

# Unit test for configuration URL generation

def test_settings_get_url():
    print("\n=== Тест: генерируем строку URL из Settings ===")
    settings = Settings()
    url = settings.get_url() 
    print(f"Полученный URL: {url}")
    assert url.startswith("postgresql://"), f"URL не начинается как 'postgresql://', а {url}"
    print("+Тест пройден: URL начинается с 'postgresql://'")

# Unit test for logger retrieval
from app.infrastructure.logging.logger import get_logger

def test_get_logger_returns_instance():
    print("\n=== Тест: получение экземпляра логгера ===")
    logger = get_logger("test")
    print(f"Имя логгера : {logger.name}")
    assert hasattr(logger, "name"), "Логгер не имеет аттрибута name"
    assert logger.name == "test", f"Имя логгера должно быть 'test', а {logger.name}"
    print("+ Тест пройден: получен корректный логгер")
