FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    git

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . /app

RUN chmod +x start.sh

EXPOSE 8501

CMD ["./start.sh"]
