defmodule Roll35Core.Data.Weapon do
  @moduledoc """
  Data handling for weapon and shield items.
  """

  use Roll35Core.Data.Agent, "priv/weapon.yaml"

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Types

  @item_types [:melee, :ranged, :ammo]

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    data
    |> Util.atomize_map()
    |> Enum.map(fn
      {:base, data} ->
        {:base, Util.process_base_armor_weapon_list(data)}

      {:specific, data} ->
        {:specific, Util.process_ranked_itemlist(data)}

      {:enchantments, data} ->
        {:enchantments, Util.process_enchantment_table(data)}

      {key, data} ->
        {key, Util.process_subranked_itemlist(data)}
    end)
    |> Map.new()
    |> Util.generate_tags_entry(@item_types)
  end

  defdelegate tags(agent), to: Roll35Core.Data.Agent
  defdelegate get_base(agent, base), to: Roll35Core.Data.Agent
  defdelegate random_base(agent), to: Roll35Core.Data.Agent
  defdelegate random_base(agent, tags), to: Roll35Core.Data.Agent
  defdelegate random_enchantment(agent, type, bonus), to: Roll35Core.Data.Agent
  defdelegate random_enchantment(agent, type, bonus, enchants), to: Roll35Core.Data.Agent
  defdelegate random_enchantment(agent, type, bonus, enchants, limit), to: Roll35Core.Data.Agent
  defdelegate random(agent, rank, subrank), to: Roll35Core.Data.Agent, as: :random_pattern
  defdelegate random(agent, rank, subrank, opts), to: Roll35Core.Data.Agent, as: :random_pattern

  @doc """
  Roll a random specific magic weapon
  """
  @spec random_specific(GenServer.server(), Types.rank(), Types.subrank()) :: %{
          atom() => term()
        }
  def random_specific(agent, rank, subrank)
      when Types.is_rank(rank) and Types.is_subrank(subrank) do
    Logger.debug(
      "Getting random specific item with rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
        __MODULE__
      }."
    )

    data = Roll35Core.Data.Agent.get(agent, fn data -> data.specific[rank][subrank] end)

    WeightedRandom.complex(data)
  end
end
