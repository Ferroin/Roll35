defmodule Roll35.MixProject do
  use Mix.Project

  def project do
    [
      apps_path: "apps",
      version: "2.1.7",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      name: "Roll35",
      releases: [
        roll35_docker: [
          include_executables: [:unix],
          applications: [roll35_bot: :permanent, roll35_core: :permanent],
          strip_beams: false,
          path: "/app"
        ]
      ],
      aliases: aliases()
    ]
  end

  # Dependencies listed here are available only for this
  # project and cannot be accessed from applications inside
  # the apps folder.
  #
  # Run "mix help deps" for examples and options.
  defp deps do
    [
      {:credo, "~> 1.7.0", only: :dev, runtime: false},
      {:credo_contrib, "~> 0.2.0", only: :dev, runtime: false},
      {:dialyxir, "~> 1.0", only: :dev, runtime: false},
      {:ex_doc, "~> 0.28.0", only: :dev, runtime: false},
      {:git_hooks, "~> 0.7.2", only: :dev, runtime: false}
    ]
  end

  defp aliases do
    [
      test: "test --no-start"
    ]
  end
end
