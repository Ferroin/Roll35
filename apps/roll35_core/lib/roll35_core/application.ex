defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  @impl Application
  def start(_type, _args) do
    children = [
      {Registry, keys: :unique, name: Roll35Core.Registry},
      {Roll35Core.Data.Belt, {:via, Registry, {Roll35Core.Registry, :belt}}},
      {Roll35Core.Data.Body, {:via, Registry, {Roll35Core.Registry, :body}}},
      {Roll35Core.Data.Category, {:via, Registry, {Roll35Core.Registry, :category}}},
      {Roll35Core.Data.Potion, {:via, Registry, {Roll35Core.Registry, :potion}}},
      {Roll35Core.Data.Scroll, {:via, Registry, {Roll35Core.Registry, :scroll}}},
      {Roll35Core.Data.Wand, {:via, Registry, {Roll35Core.Registry, :wand}}},
      {Roll35Core.Data.Wondrous, {:via, Registry, {Roll35Core.Registry, :wondrous}}}
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
