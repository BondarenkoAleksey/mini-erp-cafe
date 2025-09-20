FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

ENV PYTHONPATH=/app/src

COPY ./src /app/src

CMD ["uvicorn", "mini_erp_cafe.main:app", "--host", "0.0.0.0", "--port", "8000"]