defmodule Roll35Core.Data.Agent do
  @moduledoc """
  A general interface for our various data agents.

  Each agent represents one data table and provides functions to roll
  against that table.

  Individual agents are expected to `use Roll35Core.Data.Agent` as well
  as defining the expected callbacks.

  The implementation actually uses a `GenServer` instance instead of an
  `Agent` instance for two reasons:

  * It allows the initialization of the state to be asynchronous relative
    to the startup of the server. This is important because some of the
    agents need to load and process a very large amount of data, which
    would cause the overall startup sequence to be much slower due to
    how the startup of supervised processes is handled by `Supervisor`
    instances.
  * It allows us to hibernate the process when there is no active
    usage. This is important for resource efficiency because the bot is
    expected to be mostly inactive with short bouts of high frequency usage.
  """

  alias Roll35Core.Types

  require Roll35Core.Types

  defmacro __using__({name, datapath}) do
    quote do
      @call_timeout 15_000

      @behaviour Roll35Core.Data.Agent

      use GenServer

      require Roll35Core.Data.Agent
      require Roll35Core.Types
      require Logger

      @spec load_data :: term()
      def load_data do
        path = Path.join(Application.app_dir(:roll35_core), unquote(datapath))
        Logger.info("Loading data from #{path}.")
        data = YamlElixir.read_from_file!(path)

        Logger.info("Processing data from #{path}.")

        result = process_data(data)

        Logger.info("Finished processing data from #{path}.")
        result
      end

      @spec start_link(term()) :: GenServer.on_start()
      def start_link(_) do
        Logger.info("Starting #{__MODULE__}.")

        GenServer.start_link(__MODULE__, [],
          name: {:via, Registry, {Roll35Core.Registry, unquote(name)}}
        )
      end

      @impl GenServer
      def init(_) do
        {:ok, %{}, {:continue, :init}}
      end

      @impl GenServer
      def handle_continue(:init, _) do
        {:noreply, load_data()}
      end

      @impl GenServer
      def handle_call({:get, function}, _, state) do
        {:reply, function.(state), state}
      end

      @doc """
      Gets an agent value via the given anonymous function.

      The function `function` is sent to the `agent` which invokes
      the function passing the agent state. The result of the function
      invocation is returned from this function.

      `timeout` is an integer greater than zero which specifies how many
      milliseconds are allowed before the agent executes the function
      and returns the result value, or the atom `:infinity` to wait
      indefinitely. If no result is received within the specified time,
      the function call fails and the caller exits.
      """
      @spec get(GenServer.server(), (any() -> a), timeout()) :: a when a: var
      def get(server, function, timeout \\ @call_timeout) do
        GenServer.call(server, {:get, function}, timeout)
      end
    end
  end

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
      alias Roll35Core.Types

      require Roll35Core.Types

      @spec random(GenServer.server()) :: map()
      def random(agent) do
        data = get(agent, & &1)

        rank = Enum.random(Map.keys(data))
        subrank = Enum.random(Map.keys(data[rank]))

        WeightedRandom.complex(data[rank][subrank])
      end

      @spec random(GenServer.server(), Types.rank()) :: map()
      def random(agent, rank) when Types.is_rank(rank) do
        data = get(agent, & &1)

        subrank = Enum.random(Map.keys(data[rank]))

        WeightedRandom.complex(data[rank][subrank])
      end

      @spec random(GenServer.server(), Types.rank(), Types.subrank()) :: map()
      def random(agent, rank, subrank)
          when Types.is_rank(rank) and Types.is_full_subrank(subrank) do
        data = get(agent, & &1)

        WeightedRandom.complex(data[rank][subrank])
      end
    end
  end

  @doc """
  Define a set of selectors for a compound item list agent.

  This adds two versions of a `random` function, of1 and 2 arity. Eac
  one takes progressively more information indicating how to select the
  random item.

  The first simply takes the agent, and randomly determines the rank
  to select.

  The second takes the agent and a rank.
  """
  defmacro compound_itemlist_selectors do
    quote do
      @spec random(GenServer.server()) :: map()
      def random(agent) do
        data = get(agent, & &1)

        rank = Enum.random(Map.keys(data))

        WeightedRandom.complex(data[rank])
      end

      @spec random(GenServer.server(), Types.rank()) :: map()
      def random(agent, rank) when Types.is_rank(rank) do
        data = get(agent, & &1)

        WeightedRandom.complex(data[rank])
      end
    end
  end

  @doc """
  Called during agent startup to process the data loaded from disk into the correct state.
  """
  @callback process_data(list | map) :: term()
end
