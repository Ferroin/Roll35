defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  require Logger

  @impl Application
  def start(_type, _args) do
    children = [
      # Registry
      {Registry, keys: :unique, name: Roll35Core.Registry},

      # Data agent dependencies
      Roll35Core.Data.SpellDB,

      # Data agents
      # These are sorted in relative descending order of initialization time.
      Roll35Core.Data.Spell,
      Roll35Core.Data.Armor,
      Roll35Core.Data.Weapon,
      Roll35Core.Data.Belt,
      Roll35Core.Data.Body,
      Roll35Core.Data.Category,
      Roll35Core.Data.Chest,
      Roll35Core.Data.Classes,
      Roll35Core.Data.Eyes,
      Roll35Core.Data.Feet,
      Roll35Core.Data.Hand,
      Roll35Core.Data.Headband,
      Roll35Core.Data.Head,
      Roll35Core.Data.Keys,
      Roll35Core.Data.Neck,
      Roll35Core.Data.Potion,
      Roll35Core.Data.Ring,
      Roll35Core.Data.Rod,
      Roll35Core.Data.Scroll,
      Roll35Core.Data.Shoulders,
      Roll35Core.Data.Slotless,
      Roll35Core.Data.Staff,
      Roll35Core.Data.Wand,
      Roll35Core.Data.Wondrous,
      Roll35Core.Data.Wrists
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    result = Supervisor.start_link(children, opts)

    Logger.notice("Roll35 Core started.")

    result
  end
end
