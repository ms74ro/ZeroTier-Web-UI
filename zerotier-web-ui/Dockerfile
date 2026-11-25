FROM python:3.12-alpine

RUN apk add --no-cache tzdata

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY favicon.svg .
COPY language ./language

EXPOSE 8080

CMD ["python", "app.py"]
