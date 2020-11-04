defmodule Roll35Core.Data.Wondrous do
  @moduledoc """
  Data handling for wondrous item slots.
  """

  use Agent

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger
  require Types

  @datapath "priv/wondrous.yaml"

  @spec start_link(atom) :: Agent.on_start()
  def start_link(name) do
    Agent.start_link(&load_data/0, name: name)
  end

  @doc """
  Load the wondrous item slot data from disk. Used to prepare the initial
  state for the agent.
  """
  @spec load_data :: %{Types.rank() => [%{weight: pos_integer, value: String.t()}]}
  def load_data do
    path = Path.join(Application.app_dir(:roll35_core), @datapath)
    Logger.info("Loading data for wondrous item slots from #{path}.")
    data = YamlElixir.read_from_file!(path)

    Logger.info("Processing data for wondrous item slots.")

    result =
      Enum.map(data, fn item ->
        item
        |> Util.atomize_map()
        |> Map.update!(:value, &Types.slot_from_string/1)
      end)

    Logger.info("Finished processing data for wondrous item slots.")
    result
  end

  @doc """
  Return a random item slot.
  """
  @spec random(Agent.agent()) :: Types.slot()
  def random(agent) do
    WeightedRandom.complex(Agent.get(agent, & &1))
  end
end
