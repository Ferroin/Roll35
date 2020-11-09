import Config

config :logger,
  level: String.to_existing_atom(System.get_env("ELIXIR_LOG_LEVEL", "notice")),
  truncate: :infinity

config :roll35_core,
  spell_db_rev:
    "dev-#{Calendar.ISO |> DateTime.utc_now() |> DateTime.to_unix(:second) |> Integer.to_string()}"

config :git_hooks,
  verbose: true,
  hooks: [
    pre_commit: [
      tasks: [
        "mix format",
        "mix docs",
        "mix compile --force",
        "mix credo --format oneline"
      ]
    ],
    pre_push: [
      tasks: [
        "mix credo --strict --format oneline",
        "mix test"
      ]
    ]
  ]
