FROM python:3.7

COPY requirements.txt /
COPY requirements_dev.txt /
RUN pip install -r /requirements.txt
RUN pip install -r /requirements_dev.txt

STOPSIGNAL SIGINT
