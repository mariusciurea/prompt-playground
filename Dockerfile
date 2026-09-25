FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Pass the key at runtime:  docker run -p 8501:8501 --env-file .env <image>
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
