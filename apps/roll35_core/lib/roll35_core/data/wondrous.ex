defmodule Roll35Core.Data.Wondrous do
  @moduledoc """
  Data handling for wondrous item slots.
  """

  use Roll35Core.Data.Agent

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Enum.map(data, fn item ->
      item
      |> Util.atomize_map()
      |> Map.update!(:value, &Types.slot_from_string/1)
    end)
  end

  @doc """
  Return a random item slot.
  """
  @spec random(GenServer.server()) :: Types.slot()
  def random(agent) do
    Logger.debug("Rolling random slot.")

    data = Roll35Core.Data.Agent.get(agent, & &1)

    Util.random(data)
  end
end
