import Config

config :roll35_core,
  spell_db_rev:
    "prod-#{
      Calendar.ISO |> DateTime.utc_now() |> DateTime.to_unix(:second) |> Integer.to_string()
    }"
