defmodule Roll35Core.Data.Armor do
  @moduledoc """
  Data handling for armor and shield items.
  """

  use Roll35Core.Data.Agent, {:armor, "priv/armor.yaml"}

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Types

  @item_types [:armor, :shield]

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    data
    |> Util.atomize_map()
    |> Enum.map(fn
      {:base, data} ->
        {:base, Util.process_base_armor_weapon_list(data)}

      {:specific, data} ->
        {:specific,
         data
         |> Enum.map(fn {key, value} ->
           {key, Util.process_ranked_itemlist(value)}
         end)
         |> Map.new()}

      {:enchantments, data} ->
        {:enchantments, Util.process_enchantment_table(data)}

      {key, data} ->
        {key, Util.process_subranked_itemlist(data)}
    end)
    |> Map.new()
    |> Util.generate_tags_entry(@item_types)
  end

  Roll35Core.Data.Agent.armor_weapon_selectors(@item_types)

  @doc """
  Roll a random specific item of a given type, rank, and subrank.
  """
  @spec random_specific(GenServer.server(), atom(), Types.rank(), Types.subrank()) :: %{
          atom() => term()
        }
  def random_specific(agent, type, rank, subrank)
      when type in @item_types and Types.is_rank(rank) and Types.is_subrank(subrank) do
    data = get(agent, fn data -> data.specific[type][rank][subrank] end)

    WeightedRandom.complex(data)
  end
end
