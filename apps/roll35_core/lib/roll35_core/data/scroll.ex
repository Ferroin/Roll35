defmodule Roll35Core.Data.Scroll do
  @moduledoc """
  Data handling for scrolls.
  """

  use Agent

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger
  require Types

  @datapath "priv/scroll.yaml"

  @spec start_link(atom) :: Agent.on_start()
  def start_link(name) do
    Agent.start_link(&load_data/0, name: name)
  end

  @doc """
  Load the scroll data from disk. Used to prepare the initial state for the agent.
  """
  @spec load_data :: %{Types.rank() => [%{weight: pos_integer, value: map}]}
  def load_data do
    path = Path.join(Application.app_dir(:roll35_core), @datapath)
    Logger.info("Loading data for scrolls from #{path}.")
    data = YamlElixir.read_from_file!(path)

    Logger.info("Processing data for scrolls.")

    result = Util.process_compound_itemlist(data)

    Logger.info("Finished processing data for scrolls.")
    result
  end

  @doc """
  Return a random item scroll.
  """
  @spec random(Agent.agent()) :: map()
  def random(agent) do
    rank = Enum.random(Types.ranks())

    WeightedRandom.complex(Agent.get(agent, fn i -> i[rank] end))
  end

  @doc """
  Return a random item scroll of a specific rank.
  """
  @spec random(Agent.agent(), Types.rank()) :: map()
  def random(agent, rank) when Types.is_rank(rank) do
    WeightedRandom.complex(Agent.get(agent, fn i -> i[rank] end))
  end
end
