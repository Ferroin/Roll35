FROM python:3.9-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apk add --no-cache alpine-sdk && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del alpine-sdk

COPY data.yaml ./
COPY roll35.py ./

CMD [ "python", "./roll35.py" ]
