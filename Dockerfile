FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

CMD ["python", "main.py"]
