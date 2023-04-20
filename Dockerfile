FROM python:3.10-alpine AS builder

RUN apk update && \
    apk add --no-cache alpine-sdk && \
    pip install virtualenv

COPY / /app

WORKDIR /app

RUN virtualenv /app/venv

RUN . /app/venv/bin/activate && pip install -r /app/requirements.txt

FROM python:3.10-alpine AS runtime

COPY --from=builder /app /app

CMD [ "/app/run.sh" ]
