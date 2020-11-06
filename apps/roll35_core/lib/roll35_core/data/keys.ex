defmodule Roll35Core.Data.Keys do
  @moduledoc """
  Data handling for template keys.
  """

  use Roll35Core.Data.Agent, "priv/keys.yaml"

  alias Roll35Core.Util

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
              if item.type in [:flat_proportional, :grouped_proportional] do
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
              else
                item
              end
            end).()
      }
    end)
    |> Map.new()
  end

  @doc """
  Select a random entry from the given set of items.

  This is used for flat and proportional itemlists.
  """
  @spec random(GenServer.server(), atom()) :: String.t()
  def random(agent, key) do
    data = Map.fetch!(get(agent, & &1), key)

    if is_map(data[0]) do
      WeightedRandom.complex(data)
    else
      Enum.random(data)
    end
  end

  @doc """
  Select a random entry from the given set and subset of items.

  This is used for grouped and grouped prooportional itemlists.
  """
  @spec random(GenServer.server(), atom(), term()) :: String.t()
  def random(agent, key, subkey) do
    data =
      agent
      |> get(& &1)
      |> Map.fetch!(key)
      |> Map.fetch!(subkey)

    if is_map(data[0]) do
      WeightedRandom.complex(data)
    else
      Enum.random(data)
    end
  end
end
