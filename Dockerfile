FROM python:3.12-slim

# Рабочая директория
WORKDIR /app

# Копируем файлы зависимостей и ставим их
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install alembic[mako] asyncpg psycopg2-binary

# Копируем исходники
COPY ./src ./src
COPY ./alembic ./alembic
COPY alembic.ini .

# PYTHONPATH, чтобы импорты работали внутри контейнера
ENV PYTHONPATH=/app/src

# Команда по умолчанию
CMD ["uvicorn", "mini_erp_cafe.main:app", "--host", "0.0.0.0", "--port", "8000"]
