import Config

config :logger,
  level: String.to_existing_atom(System.get_env("LOG_LEVEL", "notice")),
  truncate: :infinity

config :roll35_core,
  data_path: System.get_env("DATA_PATH", Application.app_dir(:roll35_core, "data"))
