import Config

config :logger, :console, format: "$time $metadata[$level] $levelpad$message\n"

import_config "#{Mix.env()}.exs"
