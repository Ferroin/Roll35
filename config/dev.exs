import Config

config :git_hooks,
  verbose: true,
  hooks: [
    pre_commit: [
      tasks: [
        "mix format --check-formatted",
        "mix compile --force",
        "mix credo --format oneline"
      ]
    ],
    pre_push: [
      tasks: [
        "mix format --check-formatted",
        "mix compile --force",
        "mix credo --strict --format oneline",
        "mix dialyzer",
        "mix test"
      ]
    ]
  ]
