FROM nvidia/cuda:8.0-runtime
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && \
    apt-get -y install python3 curl

RUN curl -sSO https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py && \
    rm get-pip.py

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app/
CMD /app/start.sh
