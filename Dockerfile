FROM alpine:3.22

ARG VERSION=dev
ARG BUILD_PKGS="alpine-sdk libffi-dev py3-setuptools-rust python3-dev"

RUN apk update && \
    apk upgrade --no-cache && \
    apk add --no-cache poetry \
                       libffi

WORKDIR /app

COPY / /app

RUN apk add --no-cache ${BUILD_PKGS} && \
    poetry install --only main && \
    apk del --no-cache ${BUILD_PKGS}

RUN poetry run /app/scripts/version-check.sh ${VERSION}

CMD [ "/usr/bin/poetry", "run", "roll35-bot" ]

LABEL org.opencontainers.image.title="Roll35"
LABEL org.opencontainers.image.description="A Discord bot for rolling magic items for Pathfinder 1e."
LABEL org.opencontainers.image.url="https://github.com/Ferroin/Roll35"
LABEL org.opencontainers.image.source="https://github.com/Ferroin/Roll35"
LABEL org.opencontainers.image.version="${VERSION}"
