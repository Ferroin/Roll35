defmodule Roll35Core.Data.Keys do
  @moduledoc """
  Data handling for template keys.
  """

  use Roll35Core.Data.Agent

  alias Roll35Core.Util

  require Logger

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    data
    |> Util.atomize_map()
    |> Enum.map(fn {key, value} ->
      {
        key,
        value
        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        |> Map.update!(:type, &String.to_atom/1)
        |> (fn item ->
              case item.type do
                :flat_proportional ->
                  Map.update!(item, :data, fn data ->
                    Enum.map(data, &Util.atomize_map/1)
                  end)

                :grouped_proportional ->
                  Map.update!(item, :data, fn data ->
                    data
                    |> Enum.map(fn {key, value} ->
                      {
                        key,
                        Enum.map(value, &Util.atomize_map/1)
                      }
                    end)
                    |> Map.new()
                  end)

                _ ->
                  item
              end
            end).()
      }
    end)
    |> Map.new()
  end

  @doc """
  Select a random entry from the given set of items.
  """
  @spec random(atom()) :: String.t()
  def random(key) when is_atom(key) do
    Logger.debug("Getting random value from key #{inspect(key)}.")

    data =
      Roll35Core.Data.Agent.get({:via, Registry, {Roll35Core.Registry, :keys}}, & &1[key].data)

    if is_map(Enum.at(data, 0)) do
      WeightedRandom.complex(data)
    else
      Enum.random(data)
    end
  end

  @doc """
  Select a random entry from the given set and subset of items.
  """
  @spec random(atom(), term()) :: String.t()
  def random(key, subkey) when is_atom(key) do
    Logger.debug("Getting random value from key #{inspect({key, subkey})}.")

    data =
      {:via, Registry, {Roll35Core.Registry, :keys}}
      |> Roll35Core.Data.Agent.get(& &1[key].data)
      |> Map.fetch!(subkey)

    if is_map(Enum.at(data, 0)) do
      WeightedRandom.complex(data)
    else
      Enum.random(data)
    end
  end
end
