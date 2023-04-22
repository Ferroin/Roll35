FROM python:3.11-alpine AS builder

ARG VERSION=dev

RUN apk update && \
    apk add --no-cache alpine-sdk \
                       libffi-dev \
                       py3-setuptools-rust \
                       py3-virtualenv \
                       python3-dev

RUN virtualenv /app/venv

WORKDIR /app

COPY /requirements.txt /app

RUN . /app/venv/bin/activate && MAKEOPTS="-j$(nproc)" pip install -r /app/requirements.txt

COPY /roll35 /app/roll35
COPY /scripts/version-check.sh /app/scripts/version-check.sh

RUN . /app/venv/bin/activate && /app/scripts/version-check.sh ${VERSION}

FROM python:3.11-alpine AS runtime

ARG VERSION=dev

COPY --from=builder /app/roll35 /app/roll35
COPY /*.md /app
COPY /scripts/run.sh /app/scripts/run.sh

CMD [ "/app/scripts/run.sh" ]

LABEL org.opencontainers.image.title="Roll35"
LABEL org.opencontainers.image.description="A Discord bot for rolling magic items for Pathfinder 1e."
LABEL org.opencontainers.image.url="https://github.com/Ferroin/Roll35"
LABEL org.opencontainers.image.source="https://github.com/Ferroin/Roll35"
LABEL org.opencontainers.image.version="${VERSION}"
