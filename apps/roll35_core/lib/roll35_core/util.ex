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
  values for `t:Roll35Core.Types.item_rank/1` with each such key
  bearing a weight to use for the entry when rolling a random item of
  the corresponding rank. All the remaining keys are placed as-is into
  a map which serves as the value to be returned the weighted random
  selection.
  """
  @spec process_compound_itemlist(nonempty_list(%{atom => any})) :: %{
          Types.rank() => nonempty_list(%{atom => any})
        }
  def process_compound_itemlist(data) when is_list(data) do
    Types.ranks()
    |> Enum.map(fn rank ->
      {
        rank,
        Enum.map(data, fn entry ->
          {_, value} = Map.split(entry, Types.ranks())
          %{weight: entry[rank], value: value}
        end)
      }
    end)
    |> Map.new()
  end
end
