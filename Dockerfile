FROM python:3.9

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git libgl1 libmagic1

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt && chmod -R +x /app

COPY app.py /app/app.py
COPY network.py /app/network.py
COPY alerts.py /app/alerts.py
COPY streams.py /app/streams.py
COPY templates /app/templates
COPY static /app/static
RUN chmod -R +x /app


EXPOSE 5000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["sh", "-c", "/app/entrypoint.sh"]
