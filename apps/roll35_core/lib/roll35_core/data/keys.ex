defmodule Roll35Core.Data.Keys do
  @moduledoc """
  Data handling for template keys.
  """

  use Roll35Core.Data.Agent

  alias Roll35Core.Util

  require Logger

  @default_server {:via, Registry, {Roll35Core.Registry, :keys}}

  defp process_proportional_lists(item) do
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
  end

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
        |> process_proportional_lists()
      }
    end)
    |> Map.new()
  end

  @doc """
  Get a list of all known keys of a given type.
  """
  @spec get_keys(GenServer.server(), atom()) :: [atom()]
  def get_keys(agent, type) do
    data = Roll35Core.Data.Agent.get(agent, & &1)

    data
    |> Stream.filter(fn {_, value} ->
      value.type == type
    end)
    |> Stream.map(fn {key, _} -> key end)
    |> Enum.to_list()
  end

  @doc """
  Get a list of known subkeys for a given key.
  """
  @spec get_subkeys(GenServer.server(), atom()) :: {:ok, [term()]} | {:error, term()}
  def get_subkeys(agent, key) do
    data = Roll35Core.Data.Agent.get(agent, & &1[key])

    if data.type in [:grouped, :grouped_proportional] do
      {:ok, Map.keys(data.data)}
    else
      {:error, :invalid_key_type}
    end
  end

  @doc """
  Select a random entry using a given set of parameters.
  """
  @spec random(GenServer.server(), keyword()) :: String.t()
  def random(agent, opts)

  def random(agent, key: key, subkey: subkey) do
    Logger.debug("Getting random value from key #{inspect({key, subkey})}.")

    data =
      agent
      |> Roll35Core.Data.Agent.get(& &1[key].data)
      |> Map.fetch!(subkey)

    Util.random(data)
  end

  def random(agent, key: key) do
    Logger.debug("Getting random value from key #{inspect(key)}.")

    data = Roll35Core.Data.Agent.get(agent, & &1[key].data)

    Util.random(data)
  end

  @doc """
  Select a random entry using a given set of parameters from the default server.
  """
  @spec random(keyword()) :: String.t()
  def random(opts) do
    random(@default_server, opts)
  end
end
