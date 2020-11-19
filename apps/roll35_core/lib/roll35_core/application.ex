defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  require Logger

  @impl Application
  def start(_type, _args) do
    Enum.each(
      [
        "db"
      ],
      fn item ->
        path = Path.join(Application.fetch_env!(:roll35_core, :data_path), "db")

        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        Application.put_env(:roll35_core, String.to_atom("#{item}_path"), path, persistent: true)

        File.mkdir_p!(path)
      end
    )

    children = [
      # Registry
      {Registry, keys: :unique, name: Roll35Core.Registry}

      # Data agents
      | Roll35Core.Data.Agent.agents()
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    result = Supervisor.start_link(children, opts)

    Logger.notice("Roll35 Core started.")

    result
  end
end
