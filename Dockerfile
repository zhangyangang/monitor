FROM nvidia/cuda
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && \
    apt-get -y install python3 curl

RUN curl -sSO https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py && \
    rm get-pip.py

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app/
CMD python3 /app/gpu_stats.py 70dc48f582b7a371519f6f09a8c2f016b22e97cf67b2221e22ebc27915118479
