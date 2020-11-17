FROM elixir:1.11.2-alpine AS builder

RUN apk add --no-cache alpine-sdk

RUN mix local.hex --force

RUN mix local.rebar --force

RUN mkdir -p /build /app /build/apps/roll35_core /build/apps/roll35_bot

COPY mix.exs mix.lock /build/
COPY apps/roll35_bot/mix.exs /build/apps/roll35_bot/
COPY apps/roll35_core/mix.exs /build/apps/roll35_core/
COPY config /build/config

WORKDIR /build

RUN mix deps.get --only prod

RUN MIX_ENV=prod mix deps.compile --skip-local-deps

COPY apps /build/apps

RUN MIX_ENV=prod mix release roll35_docker

FROM alpine:3.12 as runtime

RUN apk add --no-cache ncurses-libs

ENV LOG_LEVEL="notice"
ENV DATA_PATH="/data"

VOLUME [ "/data" ]

COPY ./healthcheck.sh /healthcheck.sh
COPY --from=builder /app /app

CMD [ "/app/bin/roll35_docker", "start" ]

HEALTHCHECK --interval=60s --timeout=10s --retries=3 CMD [ "/healthcheck.sh" ]
