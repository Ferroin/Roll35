FROM elixir:1.11.2-alpine AS builder

RUN mkdir -p /build /app

RUN apk add --no-cache alpine-sdk

RUN mix local.hex --force

RUN mix local.rebar --force

COPY . /build

WORKDIR /build

RUN mix deps.get

RUN MIX_ENV=prod mix release roll35_docker

FROM alpine:3.12

RUN mkdir -p /app

RUN apk add --no-cache ncurses-libs

ENV LOG_LEVEL="notice"

COPY --from=builder /app /app

CMD [ "/app/bin/roll35_docker", "start" ]
