defmodule Roll35Core.Util do
  @moduledoc """
  Utility functions for the Roll35Core.
  """

  alias Roll35Core.Types

  defp make_weighted_entry(entry) do
    {_, value} = Map.split(entry, [:weight])
    %{weight: entry.weight, value: value}
  end

  @doc """
  Roll a random item from a list.

  If the list is a list of maps with `weight` and `value` keys, then
  we make a weighted selection based on that info and return the
  value. Otherwise, this is the same as `Enum.random/1`.
  """
  @spec random([term]) :: term()
  def random(items) do
    firstitem = Enum.at(items, 0)

    if is_map(firstitem) and Map.has_key?(firstitem, :weight) and Map.has_key?(firstitem, :value) do
      items
      |> Stream.flat_map(fn item ->
        item.value
        |> Stream.iterate(fn i -> i end)
        |> Stream.take(item.weight)
        |> Enum.to_list()
      end)
      |> Enum.random()
    else
      Enum.random(items)
    end
  end

  @doc """
  Convert string keys in a map into atoms.

  This operates recursively, processing any maps that are values within
  the passed map.
  """
  @spec atomize_map(%{(atom | String.t()) => any}) :: %{atom => any}
  def atomize_map(map) when is_map(map) do
    Enum.reduce(map, %{}, fn
      {key, value}, acc when is_binary(key) and is_map(value) ->
        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        Map.put(acc, String.to_atom(key), atomize_map(value))

      {key, value}, acc when is_binary(key) ->
        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        Map.put(acc, String.to_atom(key), value)

      {key, value}, acc when is_map(value) ->
        Map.put(acc, key, atomize_map(value))

      {key, value}, acc ->
        Map.put(acc, key, value)
    end)
  end

  @doc """
  Process compound list of weighted values.

  Each list entry must be a map with keys coresponding to the possible
  values for `t:Roll35Core.Types.rank()/1` with each such key bearing
  a weight to use for the entry when rolling a random item of the
  corresponding rank. All the remaining keys are placed as-is into a map
  which serves as the value to be returned the weighted random selection.
  """
  @spec process_compound_itemlist(nonempty_list(%{any => any})) :: Types.itemlist()
  def process_compound_itemlist(data) when is_list(data) do
    newdata = Enum.map(data, &atomize_map/1)

    Types.ranks()
    |> Enum.map(fn rank ->
      {
        rank,
        newdata
        |> Enum.map(fn entry ->
          {_, value} = Map.split(entry, Types.ranks())
          %{weight: entry[rank], value: value}
        end)
        |> Enum.filter(fn entry ->
          entry.weight != 0
        end)
      }
    end)
    |> Map.new()
  end

  @doc """
  Process ranked list of weighted values.

  This takes a map of ranks to maps of subranks to lists of maps of
  weighted items, and processes them into the format used by our weighted
  random selection in various data agent modules.
  """
  @spec process_ranked_itemlist(map) :: Types.ranked_itemlist()
  def process_ranked_itemlist(data) when is_map(data) do
    newdata = atomize_map(data)

    ranks =
      if :minor in Map.keys(newdata) do
        Types.ranks()
      else
        Types.limited_ranks()
      end

    ranks
    |> Enum.map(fn rank ->
      value = process_subranked_itemlist(newdata[rank])

      {rank, value}
    end)
    |> Map.new()
  end

  @doc """
  Process a subranked list of weighted values.

  This takes a map of subranks to lists of maps of weighted items and
  processes them into the format used by our weighted random selection
  in various data agent modules.
  """
  @spec process_subranked_itemlist(map) :: Types.subranked_itemlist()
  def process_subranked_itemlist(data) when is_map(data) do
    map = atomize_map(data)

    subranks =
      if :least in Map.keys(map) do
        Types.full_subranks()
      else
        Types.subranks()
      end

    subranks
    |> Enum.map(fn subrank ->
      value =
        Enum.map(map[subrank], fn entry ->
          entry
          |> atomize_map()
          |> make_weighted_entry()
        end)

      {subrank, value}
    end)
    |> Map.new()
  end

  @doc """
  Process a base weapon or base armor list.

  This takes a list of base item maps and converts all the keys to atoms,
  as well as modifying the type and tags entries to have atom values.
  """
  @spec process_base_armor_weapon_list(list()) :: list()
  def process_base_armor_weapon_list(data) do
    Enum.map(data, fn entry ->
      entry
      |> atomize_map()
      # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
      |> Map.update!(:type, &String.to_atom/1)
      |> Map.update!(:tags, fn data ->
        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        Enum.map(data, &String.to_atom/1)
      end)
    end)
  end

  @doc """
  Process an armor or weapon enchantment table.
  """
  @spec process_enchantment_table(map()) :: map()
  def process_enchantment_table(data) do
    data
    |> Enum.map(fn {key, value} ->
      {key,
       value
       |> Enum.map(fn {key, value} ->
         {key,
          Enum.map(value, fn entry ->
            entry = atomize_map(entry)
            {_, value} = Map.split(entry, [:weight])

            value =
              if Map.has_key?(value, :limit) do
                Map.update!(value, :limit, fn item ->
                  item
                  |> Enum.map(fn {key, value} ->
                    {
                      key,
                      # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
                      Enum.map(value, &String.to_atom/1)
                    }
                  end)
                  |> Map.new()
                end)
              else
                value
              end

            value =
              if Map.has_key?(value, :remove) do
                Map.update!(value, :remove, fn item ->
                  # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
                  Enum.map(item, &String.to_atom/1)
                end)
              else
                value
              end

            value =
              if Map.has_key?(value, :add) do
                Map.update!(value, :add, fn item ->
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
    |> Map.new()
  end

  @doc """
  Process an armor or weapon agent state to add a list of all tags.
  """
  @spec generate_tags_entry(%{:base => list(), atom() => term()}, [atom()]) :: %{
          :base => list(),
          :tags => list(),
          atom() => term()
        }
  def generate_tags_entry(data, base_tags \\ []) do
    tags =
      Enum.reduce(data.base, MapSet.new(base_tags), fn item, acc ->
        Enum.reduce(item.tags, acc, fn tag, acc ->
          MapSet.put(acc, tag)
        end)
      end)

    Map.put(data, :tags, MapSet.to_list(tags))
  end

  @doc """
  Square an integer.
  """
  @spec squared(integer()) :: integer()
  def squared(x) when is_integer(x) do
    x * x
  end
end
