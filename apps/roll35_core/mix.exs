defmodule Roll35Core.MixProject do
  use Mix.Project

  def project do
    [
      app: :roll35_core,
      version: "4.0.5",
      build_path: "../../_build",
      config_path: "../../config/config.exs",
      deps_path: "../../deps",
      lockfile: "../../mix.lock",
      elixir: "~> 1.11",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      aliases: aliases()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: [:logger, :eex],
      mod: {Roll35Core.Application, []},
      registered: [Roll35Core.Supervisor, Roll35Core.Registry]
    ]
  end

  # Run "mix help deps" to learn about dependencies.
  defp deps do
    [
      {:credo, "~> 1.5.0", only: :dev, runtime: false},
      {:credo_contrib, "~> 0.2.0", only: :dev, runtime: false},
      {:dialyxir, "~> 1.0", only: :dev, runtime: false},
      {:ex_doc, "~> 0.24.1", only: :dev, runtime: false},
      {:git_hooks, "~> 0.6.2", only: :dev, runtime: false},
      {:sqlitex, "~> 1.7"},
      {:yaml_elixir, "~> 2.6"}
    ]
  end

  defp aliases do
    [
      test: "test --no-start"
    ]
  end
end
