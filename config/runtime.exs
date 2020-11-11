import Config

config :logger,
  level: String.to_existing_atom(System.get_env("LOG_LEVEL", "notice")),
  truncate: :infinity
