import Config

config :logger,
  level: String.to_existing_atom(System.get_env("ELIXIR_LOG_LEVEL", "notice")),
  truncate: :infinity

config :roll35_core,
  spell_db_rev:
    "test-#{
      Calendar.ISO |> DateTime.utc_now() |> DateTime.to_unix(:second) |> Integer.to_string()
    }"
