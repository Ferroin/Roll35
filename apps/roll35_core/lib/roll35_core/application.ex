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
      {Roll35Core.Data.Chest, {:via, Registry, {Roll35Core.Registry, :chest}}},
      {Roll35Core.Data.Eyes, {:via, Registry, {Roll35Core.Registry, :eyes}}},
      {Roll35Core.Data.Feet, {:via, Registry, {Roll35Core.Registry, :feet}}},
      {Roll35Core.Data.Hand, {:via, Registry, {Roll35Core.Registry, :hand}}},
      {Roll35Core.Data.Headband, {:via, Registry, {Roll35Core.Registry, :headband}}},
      {Roll35Core.Data.Head, {:via, Registry, {Roll35Core.Registry, :head}}},
      {Roll35Core.Data.Neck, {:via, Registry, {Roll35Core.Registry, :neck}}},
      {Roll35Core.Data.Potion, {:via, Registry, {Roll35Core.Registry, :potion}}},
      {Roll35Core.Data.Scroll, {:via, Registry, {Roll35Core.Registry, :scroll}}},
      {Roll35Core.Data.Shoulders, {:via, Registry, {Roll35Core.Registry, :shoulders}}},
      {Roll35Core.Data.Slotless, {:via, Registry, {Roll35Core.Registry, :slotless}}},
      {Roll35Core.Data.Wand, {:via, Registry, {Roll35Core.Registry, :wand}}},
      {Roll35Core.Data.Wondrous, {:via, Registry, {Roll35Core.Registry, :wondrous}}},
      {Roll35Core.Data.Wrists, {:via, Registry, {Roll35Core.Registry, :wrists}}}
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
