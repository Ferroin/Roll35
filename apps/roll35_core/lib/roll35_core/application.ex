defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      {Roll35Core.Data.Belt, :belt},
      {Roll35Core.Data.Body, :body},
      {Roll35Core.Data.Category, :category},
      {Roll35Core.Data.Potion, :potion},
      {Roll35Core.Data.Scroll, :scroll},
      {Roll35Core.Data.Wand, :wand},
      {Roll35Core.Data.Wondrous, :wondrous}
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
