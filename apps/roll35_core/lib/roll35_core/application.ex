defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      {Roll35Core.Data.Category, :category}
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
