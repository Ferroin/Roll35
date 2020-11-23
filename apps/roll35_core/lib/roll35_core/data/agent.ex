defmodule Roll35Core.Data.Agent do
  @moduledoc """
  A general interface for our various data agents.

  Each agent represents one data table and provides functions to roll
  against that table.

  Individual agents are expected to `use Roll35Core.Data.Agent` as well
  as defining the expected callbacks.

  The implementation actually uses a `GenServer` instance instead of an
  `Agent` instance because it allows us to handle initialization
  asynchronously.
  """

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Roll35Core.Types

  require Logger

  @call_timeout 15_000

  defmacro __using__(_) do
    quote do
      @behaviour Roll35Core.Data.Agent

      use GenServer

      require Roll35Core.Data.Agent
      require Roll35Core.Types
      require Logger

      @spec load_data(Path.t()) :: term()
      def load_data(path) do
        path = Path.join(Application.app_dir(:roll35_core), path)
        data = YamlElixir.read_from_file!(path)
        result = process_data(data)

        Logger.info("Finished initializing #{__MODULE__}.")
        result
      end

      @spec start_link(name: GenServer.server(), datapath: Path.t()) :: GenServer.on_start()
      def start_link(name: name, datapath: datapath) do
        Logger.info("Starting #{__MODULE__}.")

        GenServer.start_link(__MODULE__, datapath, name: name)
      end

      @impl GenServer
      def init(datapath) do
        {:ok, %{datapath: datapath}, {:continue, :init}}
      end

      @impl GenServer
      def handle_continue(:init, state) do
        {:noreply, load_data(state.datapath)}
      end

      @impl GenServer
      def handle_call({:get, function}, _, state) do
        {:reply, function.(state), state}
      end
    end
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

  @doc """
  Get a random item from a ranked item list based on a rank and subrank
  """
  @spec random_ranked(GenServer.server(), Types.rank(), Types.full_subrank()) :: Types.item()
  def random_ranked(agent, rank, subrank) do
    Logger.debug(
      "Getting random item with rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
        __MODULE__
      }."
    )

    data = get(agent, & &1)

    Util.random(data[rank][subrank])
  end

  @doc """
  Get a random item from a ranked item list based on a rank.
  """
  @spec random_ranked(GenServer.server(), Types.rank()) :: Types.item()
  def random_ranked(agent, rank) do
    Logger.debug(
      "Getting random item with rank #{inspect(rank)} and random subrank from #{__MODULE__}."
    )

    data = get(agent, & &1)

    subrank = Util.random(Map.keys(data[rank]))

    Util.random(data[rank][subrank])
  end

  @doc """
  Get a random item from a ranked item list.
  """
  @spec random_ranked(GenServer.server()) :: Types.item()
  def random_ranked(agent) do
    Logger.debug("Getting random item with random rank and subrank from #{__MODULE__}.")

    data = get(agent, & &1)

    rank = Util.random(Map.keys(data))
    subrank = Util.random(Map.keys(data[rank]))

    Util.random(data[rank][subrank])
  end

  @doc """
  Get a random item from a compound itemlist for a given rank.
  """
  @spec random_compound(GenServer.server(), Types.rank()) :: Types.item()
  def random_compound(agent, rank) do
    Logger.debug("Getting random item with rank #{inspect(rank)} from #{__MODULE__}.")

    data = get(agent, & &1)

    Util.random(data[rank])
  end

  @doc """
  Get a random item from a compound itemlist.
  """
  @spec random_compound(GenServer.server()) :: Types.item()
  def random_compound(agent) do
    Logger.debug("Getting random item with random rank from #{__MODULE__}.")

    data = get(agent, & &1)

    rank = Util.random(Map.keys(data))

    Util.random(data[rank])
  end

  @doc """
  Get a specific base item by name.
  """
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

  @doc """
  Get a random base item, possibly limited by a tag list.
  """
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
      |> Enum.to_list()
      |> Util.random()
    rescue
      _ in Enum.EmptyError -> nil
    end
  end

  @doc """
  Get a random enchantment limited by the given parameters.
  """
  @spec random_enchantment(
          GenServer.server(),
          atom(),
          non_neg_integer(),
          list(String.t()),
          list(atom())
        ) :: %{atom() => term()} | nil
  def random_enchantment(agent, type, bonus, enchants \\ [], limit \\ []) do
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
      Util.random(possible)
    end
  end

  @doc """
  Get a random armor or weapon pattern.
  """
  @spec random_pattern(GenServer.server(), Types.rank(), Types.subrank(), keyword()) :: %{
          atom() => term()
        }
  def random_pattern(agent, rank, subrank, opts \\ [])

  def random_pattern(agent, rank, subrank, no_specific: true)
      when Types.is_rank(rank) and Types.is_subrank(subrank) do
    Logger.info(
      "Getting random item of rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
        __MODULE__
      }, ignoring specific rolls."
    )

    data = get(agent, fn data -> data[rank][subrank] end)

    data
    |> Enum.filter(fn item -> :specific not in Map.keys(item.value) end)
    |> Util.random()
  end

  def random_pattern(agent, rank, subrank, _)
      when Types.is_rank(rank) and Types.is_subrank(subrank) do
    Logger.info(
      "Getting random item of rank #{inspect(rank)} and subrank #{inspect(subrank)} from #{
        __MODULE__
      }."
    )

    data = get(agent, fn data -> data[rank][subrank] end)

    Util.random(data)
  end

  @doc """
  Get a list of valid weapon or armor tags.
  """
  @spec tags(GenServer.server()) :: list(atom())
  def tags(agent) do
    Logger.info("Fetching list of valid tags from #{__MODULE__}.")

    get(agent, fn data -> data.tags end)
  end

  @doc """
  Called during agent startup to process the data loaded from disk into the correct state.
  """
  @callback process_data(list | map) :: term()
end
