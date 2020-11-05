defmodule Roll35Core.Data.Macros do
  @moduledoc """
  Macros for use by the various data agents for Roll35.
  """

  alias Roll35Core.Types

  require Roll35Core.Types

  @doc """
  Defines a set of selectors for a ranked item list agent.

  This adds three versions of a `random` function, of 1, 2, and 3
  arity. Each one takes progressively more information indicating how
  to select the random item.

  The first simply takes the agent, and randomly determines the rank
  and subrank to select.

  The second takes the agent and a rank, and randomly determines the
  subrank.

  The third takes the agent, a rank, and a subrank.
  """
  defmacro ranked_itemlist_selectors do
    quote do
      @spec random(Agent.agent()) :: map()
      def random(agent) do
        data = Agent.get(agent, & &1)

        rank = Enum.random(Map.keys(data))
        subrank = Enum.random(Map.keys(data[rank]))

        WeightedRandom.complex(data[rank][subrank])
      end

      @spec random(Agent.agent(), Types.rank()) :: map()
      def random(agent, rank) when Types.is_rank(rank) do
        data = Agent.get(agent, & &1)

        subrank = Enum.random(Map.keys(data[rank]))

        WeightedRandom.complex(data[rank][subrank])
      end

      @spec random(Agent.agent(), Types.rank(), Types.subrank()) :: map()
      def random(agent, rank, subrank)
          when Types.is_rank(rank) and Types.is_full_subrank(subrank) do
        data = Agent.get(agent, & &1)

        WeightedRandom.complex(data[rank][subrank])
      end
    end
  end
end
