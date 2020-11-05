defmodule Roll35Core.Data.Category do
  @moduledoc """
  Data handling for item categories.
  """

  use Agent

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger
  require Types

  @datapath "priv/category.yaml"

  @spec start_link(atom) :: Agent.on_start()
  def start_link(name) do
    Agent.start_link(&load_data/0, name: name)
  end

  @doc """
  Load the category data from disk. Used to prepare the initial state for the agent.
  """
  @spec load_data :: %{Types.rank() => [%{weight: pos_integer(), value: Types.category()}, ...]}
  def load_data do
    path = Path.join(Application.app_dir(:roll35_core), @datapath)
    Logger.info("Loading data for item categories from #{path}.")
    data = YamlElixir.read_from_file!(path)

    Logger.info("Processing data for item categories.")

    result =
      data
      |> Util.atomize_map()
      |> Enum.map(fn {key, value} ->
        {key,
         Enum.map(value, fn entry ->
           entry
           |> Util.atomize_map()
           |> Map.update!(:value, &Types.category_from_string/1)
         end)}
      end)
      |> Map.new()

    Logger.info("Finished processing data for item categories.")
    result
  end

  @doc """
  Return a random item category.
  """
  @spec random(Agent.agent()) :: Types.category()
  def random(agent) do
    rank = Enum.random(Types.ranks())

    WeightedRandom.complex(Agent.get(agent, fn i -> i[rank] end))
  end

  @doc """
  Return a random item category of a specific rank.
  """
  @spec random(Agent.agent(), Types.rank()) :: Types.category()
  def random(agent, rank) when Types.is_rank(rank) do
    WeightedRandom.complex(Agent.get(agent, fn i -> i[rank] end))
  end
end
