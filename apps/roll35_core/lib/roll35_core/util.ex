defmodule Roll35Core.Util do
  @moduledoc """
  Utility functions for the Roll35Core.
  """

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
end
