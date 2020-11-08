defmodule Roll35Core.Data.Armor do
  @moduledoc """
  Data handling for armor and shield items.
  """

  use Roll35Core.Data.Agent, {:armor, "priv/armor.yaml"}

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Types

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    data
    |> Util.atomize_map()
    |> Enum.map(fn
      {:base, data} ->
        {:base,
         Enum.map(data, fn entry ->
           entry
           |> Util.atomize_map()
           # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
           |> Map.update!(:type, &String.to_atom/1)
           |> Map.update!(:tags, fn data ->
             # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
             Enum.map(data, &String.to_atom/1)
           end)
         end)}

      {:specific, data} ->
        {:specific,
         data
         |> Enum.map(fn {key, value} ->
           {key, Util.process_ranked_itemlist(value)}
         end)
         |> Map.new()}

      {:enchantments, data} ->
        {:enchantments,
         data
         |> Enum.map(fn {key, value} ->
           {key,
            value
            |> Enum.map(fn {key, value} ->
              {key,
               Enum.map(value, fn entry ->
                 entry = Util.atomize_map(entry)
                 {_, value} = Map.split(entry, [:weight])

                 value =
                   if Map.has_key?(value, :limit) do
                     Map.update!(value, :limit, fn item ->
                       # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
                       Enum.map(item, &String.to_atom/1)
                     end)
                   else
                     value
                   end

                 %{weight: entry.weight, value: value}
               end)}
            end)
            |> Map.new()}
         end)
         |> Map.new()}

      {key, data} ->
        {key,
         data
         |> Enum.map(fn {key, data} ->
           {
             key,
             Enum.map(data, fn entry ->
               entry = Util.atomize_map(entry)
               {_, value} = Map.split(entry, [:weight])
               %{weight: entry.weight, value: value}
             end)
           }
         end)
         |> Map.new()}
    end)
    |> Map.new()
    |> (fn data ->
          tags =
            Enum.reduce(data.base, MapSet.new([:armor, :shield]), fn item, acc ->
              Enum.reduce(item.tags, acc, fn tag, acc ->
                MapSet.put(acc, tag)
              end)
            end)

          Map.put(data, :tags, MapSet.to_list(tags))
        end).()
  end

  @doc """
  Roll a random base item.

  Optionally limited by a list of types and tags.
  """
  @spec random_base(GenServer.server(), list(atom())) :: %{atom() => term()}
  def random_base(agent, tags \\ []) do
    data = get(agent, fn data -> data.base end)

    data
    |> Stream.filter(fn item ->
      if Enum.empty?(tags) do
        true
      else
        Enum.all?(tags, fn tag ->
          tag == item.type or tag in item.tags
        end)
      end
    end)
    |> Enum.random()
  end

  @doc """
  Roll a random specific item of a given type, rank, and subrank.
  """
  @spec random_specific(GenServer.server(), atom(), Types.rank(), Types.subrank()) :: %{
          atom() => term()
        }
  def random_specific(agent, type, rank, subrank)
      when type in [:armor, :shield] and Types.is_rank(rank) and Types.is_subrank(subrank) do
    data = get(agent, fn data -> data.specific[type][rank][subrank] end)

    WeightedRandom.complex(data)
  end

  @doc """
  Roll a random enchant of a given type and bonus.

  Optionally limited by a list of existing enchantments and a list of tags.
  """
  @spec random_enchantment(
          GenServer.server(),
          atom(),
          non_neg_integer(),
          list(String.t()),
          list(atom())
        ) :: %{atom() => term()} | nil
  def random_enchantment(agent, type, bonus, enchants \\ [], limit \\ [])
      when type in [:armor, :shield] do
    data = get(agent, fn data -> data.enchantments[type][bonus] end)

    possible =
      Enum.filter(data, fn item ->
        cond do
          Map.has_key?(item, :exclude) and Enum.any?(enchants, &(&1 in item.exclude)) -> false
          Map.has_key?(item, :limit) and not Enum.any?(limit, &(&1 in item.limit)) -> false
          true -> true
        end
      end)

    if Enum.empty?(possible) do
      nil
    else
      WeightedRandom.complex(possible)
    end
  end

  @doc """
  Roll the template for a random magic armor item of a given rank and subrank.
  """
  @spec random(GenServer.server(), Types.rank(), Types.subrank()) :: %{atom() => term()}
  def random(agent, rank, subrank) when Types.is_rank(rank) and Types.is_subrank(subrank) do
    data = get(agent, fn data -> data[rank][subrank] end)

    WeightedRandom.complex(data)
  end

  @doc """
  Return a list of known tags.
  """
  @spec tags(GenServer.server()) :: list(atom())
  def tags(agent) do
    get(agent, fn data -> data.tags end)
  end
end
