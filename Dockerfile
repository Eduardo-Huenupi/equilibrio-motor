FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY core ./core
COPY apps ./apps

RUN useradd --create-home motor
USER motor

EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
