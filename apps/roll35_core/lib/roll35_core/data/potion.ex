defmodule Roll35Core.Data.Potion do
  @moduledoc """
  Data handling for potions.
  """

  use Agent

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger
  require Types

  @datapath "priv/potion.yaml"

  @spec start_link(atom) :: Agent.on_start()
  def start_link(name) do
    Agent.start_link(&load_data/0, name: name)
  end

  @doc """
  Load the potion data from disk. Used to prepare the initial state for the agent.
  """
  @spec load_data :: %{Types.rank() => [%{weight: pos_integer, value: map}]}
  def load_data do
    path = Path.join(Application.app_dir(:roll35_core), @datapath)
    Logger.info("Loading data for potions from #{path}.")
    data = YamlElixir.read_from_file!(path)

    Logger.info("Processing data for potions.")

    result = Util.process_compound_itemlist(data)

    Logger.info("Finished processing data for potions.")
    result
  end

  @doc """
  Return a random item potion.
  """
  @spec random(Agent.agent()) :: map()
  def random(agent) do
    rank = Enum.random(Types.ranks())

    WeightedRandom.complex(Agent.get(agent, fn i -> i[rank] end))
  end

  @doc """
  Return a random item potion of a specific rank.
  """
  @spec random(Agent.agent(), Types.rank()) :: map()
  def random(agent, rank) when Types.is_rank(rank) do
    WeightedRandom.complex(Agent.get(agent, fn i -> i[rank] end))
  end
end
