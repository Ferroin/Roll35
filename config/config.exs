import Config

import_config "#{Mix.env()}.exs"

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
