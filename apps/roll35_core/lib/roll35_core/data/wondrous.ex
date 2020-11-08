defmodule Roll35Core.Data.Wondrous do
  @moduledoc """
  Data handling for wondrous item slots.
  """

  use Roll35Core.Data.Agent, {:wondrous, "priv/wondrous.yaml"}

  alias Roll35Core.Types
  alias Roll35Core.Util

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
    data = get(agent, & &1)

    WeightedRandom.complex(data)
  end
end
