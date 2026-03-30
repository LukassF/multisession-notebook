FROM python:3.11-slim

WORKDIR /app

# Zainstaluj zależności systemowe
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj requirements i zainstaluj zależności Pythona
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj aplikację
COPY . .

# Expose port dla Streamlit
EXPOSE 8501

# Komenda startowa
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
