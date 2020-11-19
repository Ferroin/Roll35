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
        data = YamlElixir.read_from_file!(path)
        result = process_data(data)

        Logger.info("Finished initializing #{__MODULE__}.")
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
        Logger.debug("Getting random item with random rank and subrank from #{__MODULE__}.")

        data = get(agent, & &1)

        rank = Enum.random(Map.keys(data))
        subrank = Enum.random(Map.keys(data[rank]))

        WeightedRandom.complex(data[rank][subrank])
      end

      @spec random(GenServer.server(), Types.rank()) :: map()
      def random(agent, rank) when Types.is_rank(rank) do
        Logger.debug(
          "Getting random item with rank #{inspect(rank)} and random subrank from #{__MODULE__}."
        )

        data = get(agent, & &1)

        subrank = Enum.random(Map.keys(data[rank]))

        WeightedRandom.complex(data[rank][subrank])
      end

      @spec random(GenServer.server(), Types.rank(), Types.subrank()) :: map()
      def random(agent, rank, subrank)
          when Types.is_rank(rank) and Types.is_full_subrank(subrank) do
        Logger.debug(
          "Getting random item with rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
            __MODULE__
          }."
        )

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
        Logger.debug("Getting random item with random rank from #{__MODULE__}.")

        data = get(agent, & &1)

        rank = Enum.random(Map.keys(data))

        WeightedRandom.complex(data[rank])
      end

      @spec random(GenServer.server(), Types.rank()) :: map()
      def random(agent, rank) when Types.is_rank(rank) do
        Logger.debug("Getting random item with rank #{inspect(rank)} from #{__MODULE__}.")

        data = get(agent, & &1)

        WeightedRandom.complex(data[rank])
      end
    end
  end

  @doc """
  Define a set of selectors for an armor or weapon item agent.

  This adds a function for fetching a full list of tags, plus functions
  for fetching random base items, random enchantments, and random magic
  item templates.
  """
  defmacro armor_weapon_selectors(types) do
    quote do
      @spec get_base(GenServer.server(), String.t()) ::
              {:ok, %{atom() => term()}} | {:error, String.t()}
      def get_base(agent, name) do
        Logger.debug("Fetching bse item \"#{name}\".")

        data = get(agent, fn data -> data.base end)

        norm_name =
          name
          |> String.normalize(:nfd)
          |> String.downcase()

        result =
          Enum.find(data, fn item ->
            item.name |> String.normalize(:nfd) |> String.downcase() == norm_name
          end)

        if result == nil do
          possible =
            data
            |> Task.async_stream(
              fn item ->
                item_name =
                  item.name
                  |> String.normalize(:nfd)
                  |> String.downcase()

                cond do
                  String.starts_with?(item_name, norm_name) -> {item.name, 1.2}
                  String.ends_with?(item_name, norm_name) -> {item.name, 1.2}
                  String.contains?(item_name, norm_name) -> {item.name, 1.1}
                  true -> {item.name, String.jaro_distance(norm_name, item_name)}
                end
              end,
              max_concurrency: min(System.schedulers_online(), 4),
              ordered: false
            )
            |> Stream.map(fn {:ok, v} -> v end)
            |> Stream.filter(fn {_, d} -> d > 0.8 end)
            |> Enum.sort(fn {_, d1}, {_, d2} -> d2 >= d1 end)
            |> Enum.take(4)
            |> Enum.map(fn {i, _} -> i end)

          if possible == [] do
            {:error, "No matching items found."}
          else
            {:error,
             "\"#{name}\" is not a recognized item, did you possibly mean one of: \"#{
               Enum.join(possible, "\", \"")
             }\"?"}
          end
        else
          {:ok, result}
        end
      end

      @spec random_base(GenServer.server(), list(atom())) :: %{atom() => term()} | nil
      def random_base(agent, tags \\ []) do
        Logger.debug(
          "Getting random base item with tags matching #{inspect(tags)} from #{__MODULE__}."
        )

        data = get(agent, fn data -> data.base end)

        try do
          data
          |> Stream.filter(fn item ->
            if Enum.empty?(tags) do
              true
            else
              Enum.all?(tags, fn tag ->
                tag == item.type or tag in item.tags
              end)
            end
          end)
          |> Enum.random()
        rescue
          e in Enum.EmptyError -> nil
        end
      end

      @spec random_enchantment(
              GenServer.server(),
              atom(),
              non_neg_integer(),
              list(String.t()),
              list(atom())
            ) :: %{atom() => term()} | nil
      def random_enchantment(agent, type, bonus, enchants \\ [], limit \\ [])
          when type in unquote(types) do
        Logger.debug(
          "Getting random enchantment of type #{inspect(type)} and level #{inspect(bonus)} excluding #{
            inspect(enchants)
          } and limited by #{inspect(limit)} from #{__MODULE__}."
        )

        data = get(agent, fn data -> data.enchantments[type][bonus] end)

        possible =
          Enum.filter(data, fn item ->
            cond do
              Map.has_key?(item, :exclude) and Enum.any?(enchants, &(&1 in item.exclude)) ->
                false

              Map.has_key?(item, :limit) and Map.has_key?(item.limit, :only) and
                  not Enum.any?(limit, &(&1 in item.limit.only)) ->
                false

              Map.has_key?(item, :limit) and Map.has_key?(item.limit, :not) and
                  Enum.any?(limit, &(&1 in item.limit.not)) ->
                false

              true ->
                true
            end
          end)

        if Enum.empty?(possible) do
          nil
        else
          WeightedRandom.complex(possible)
        end
      end

      @spec random(GenServer.server(), Types.rank(), Types.subrank(), keyword()) :: %{
              atom() => term()
            }
      def random(agent, rank, subrank, opts \\ [])

      def random(agent, rank, subrank, no_specific: true)
          when Types.is_rank(rank) and Types.is_subrank(subrank) do
        Logger.info(
          "Getting random item of rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
            __MODULE__
          }, ignoring specific rolls."
        )

        data = get(agent, fn data -> data[rank][subrank] end)

        data
        |> Enum.filter(fn item -> :specific not in Map.keys(item.value) end)
        |> WeightedRandom.complex()
      end

      def random(agent, rank, subrank, _)
          when Types.is_rank(rank) and Types.is_subrank(subrank) do
        Logger.info(
          "Getting random item of rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
            __MODULE__
          }."
        )

        data = get(agent, fn data -> data[rank][subrank] end)

        WeightedRandom.complex(data)
      end

      @spec tags(GenServer.server()) :: list(atom())
      def tags(agent) do
        Logger.info("Fetching list of valid tags from #{__MODULE__}.")

        get(agent, fn data -> data.tags end)
      end
    end
  end

  @doc """
  Called during agent startup to process the data loaded from disk into the correct state.
  """
  @callback process_data(list | map) :: term()
end
