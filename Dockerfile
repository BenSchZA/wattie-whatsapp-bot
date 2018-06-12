FROM python:3.6-alpine as base

FROM base as builder

RUN mkdir /install
WORKDIR /install

COPY requirements.txt /requirements.txt

RUN pip install --install-option="--prefix=/install" -r /requirements.txt

FROM base

COPY --from=builder /install /usr
COPY src /app

WORKDIR /app

EXPOSE 8001

CMD ["python", "session_manager.py"]