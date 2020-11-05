defmodule Roll35Core.Util do
  @moduledoc """
  Utility functions for the Roll35Core.
  """

  alias Roll35Core.Types

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
        Enum.map(newdata, fn entry ->
          {_, value} = Map.split(entry, Types.ranks())
          %{weight: entry[rank], value: value}
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
      submap = atomize_map(newdata[rank])

      subranks =
        if :least in Map.keys(submap) do
          Types.full_subranks()
        else
          Types.subranks()
        end

      value =
        subranks
        |> Enum.map(fn subrank ->
          value =
            Enum.map(submap[subrank], fn entry ->
              entry
              |> atomize_map()
              |> (fn entry ->
                    {_, value} = Map.split(entry, [:weight])
                    %{weight: entry.weight, value: value}
                  end).()
            end)

          {subrank, value}
        end)
        |> Map.new()

      {rank, value}
    end)
    |> Map.new()
  end
end
