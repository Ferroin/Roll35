defmodule Roll35Bot.MixProject do
  use Mix.Project

  def project do
    [
      app: :roll35_bot,
      version: "4.1.4",
      build_path: "../../_build",
      config_path: "../../config/config.exs",
      deps_path: "../../deps",
      lockfile: "../../mix.lock",
      elixir: "~> 1.11",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      mod: {Roll35Bot.Application, []},
      extra_applications: [:logger]
    ]
  end

  # Run "mix help deps" to learn about dependencies.
  defp deps do
    [
      {:alchemy, "~> 0.6.6", hex: :discord_alchemy},
      {:credo, "~> 1.5.0", only: :dev, runtime: false},
      {:credo_contrib, "~> 0.2.0", only: :dev, runtime: false},
      {:dialyxir, "~> 1.0", only: :dev, runtime: false},
      {:ex_doc, "~> 0.25.0", only: :dev, runtime: false},
      {:git_hooks, "~> 0.6.2", only: :dev, runtime: false},
      {:roll35_core, in_umbrella: true}
    ]
  end
end
