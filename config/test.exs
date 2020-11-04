import Config

config :logger,
  level: String.to_existing_atom(System.get_env("ELIXIR_LOG_LEVEL", "notice")),
  truncate: :infinity
