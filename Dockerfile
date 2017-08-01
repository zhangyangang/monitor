FROM nvidia/cuda:latest
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && \
    apt-get -y install python curl

RUN curl -sSO https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    rm get-pip.py

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY collect.py /app/collect.py
