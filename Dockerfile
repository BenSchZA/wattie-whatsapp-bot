#FROM python:3.6 as base
#
#FROM base as builder
#
#RUN mkdir /install
#WORKDIR /install
#
#COPY requirements.txt /requirements.txt
#
##--install-option="--prefix=/install"
#ENV PYTHONUSERBASE=/install
#RUN pip install -r /requirements.txt

FROM python:3.6

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app

EXPOSE 8001

CMD ["python", "session_manager.py"]