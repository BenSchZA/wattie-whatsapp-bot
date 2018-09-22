FROM python:3.6

RUN mkdir /app
WORKDIR /app
COPY supervisord.conf /app/supervisord.conf
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y supervisor

COPY . /app

EXPOSE 8001
EXPOSE 5050

ARG DEFAULT_PASSWORD

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
