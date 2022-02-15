FROM python:3.9

COPY ./ /tmp/d20

RUN  \
apt-get update && \
apt-get install libffi-dev libfuzzy-dev && \
cd /tmp/d20 && \
pip install ssdeep && \
pip install /tmp/d20 && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /data

CMD ["d20", "-h"]
