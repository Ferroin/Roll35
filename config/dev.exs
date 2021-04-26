import Config

config :git_hooks,
  verbose: true,
  hooks: [
    pre_commit: [
      tasks: [
        {:mix_task, :format, ["--check-formatted"]},
        {:mix_task, :compile, ["--force"]},
        {:mix_task, :credo, ["--format", "oneline"]}
      ]
    ],
    pre_push: [
      tasks: [
        {:mix_task, :format, ["--check-formatted"]},
        {:mix_task, :compile, ["--force"]},
        {:mix_task, :credo, ["--strict", "--format", "oneline"]},
        {:mix_task, :dialyzer},
        {:mix_task, :test}
      ]
    ]
  ]
