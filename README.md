# Mini-ERP-Cafe

Учебный pet-project: мини ERP для кафе.  
Стек: **FastAPI, PostgreSQL, Redis, SQLAlchemy, Alembic, Celery, Docker, Pytest**.  
Цель — обучение разработке на Python.

---

## 🚀 Локальный запуск (без Docker)

1. Клонировать проект и перейти в папку:

```bash
git clone https://gitlab.com/your-repo/mini-erp-cafe.git
cd mini-erp-cafe
```
2. Создать виртуальное окружение:
```bash
python3.12 -m venv venv
source venv/bin/activate      # Linux / macOS
# или .\venv\Scripts\activate  # Windows PowerShell
```

3. Установить зависимости:
```bash
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

4. Запустить сервер:
```bash
uvicorn src.mini_erp_cafe.main:app --reload
```

Проверить:
```bash
http://127.0.0.1:8000/health
 → {"status": "ok", "timestamp": "..."}

http://127.0.0.1:8000/docs
 → Swagger UI
```

## Запуск через Docker

1. Собрать образ:
```bash
docker compose build
```

2. Запустить контейнеры:
```bash
docker compose up
```

Приложение будет доступно на http://localhost:8000
.

## Development
Форматирование кода
```bash
black src tests
isort src tests
mypy src
```

## Тесты
```bash
pytest -v
```

## 📝 TODO (MVP)

 Базовый проект и структура

 - Health-check эндпоинт
 - Подключение PostgreSQL (SQLAlchemy + Alembic)
 - Подключение Redis
 - Настройка Celery
 - CI/CD (GitLab)
 - Telegram-бот