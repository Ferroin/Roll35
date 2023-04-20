FROM python:3.10-alpine AS builder

RUN apk update && \
    apk add --no-cache alpine-sdk \
                       libffi-dev \
                       py3-setuptools-rust \
                       py3-virtualenv \
                       python3-dev

COPY / /app

WORKDIR /app

RUN virtualenv /app/venv

RUN . /app/venv/bin/activate && MAKEOPTS="$(nproc)" pip install -r /app/requirements.txt

FROM python:3.10-alpine AS runtime

COPY --from=builder /app /app

CMD [ "/app/run.sh" ]
