defmodule Roll35Core.Data.SpellDB do
  @moduledoc """
  A server for handling access to the spell database.

  This is intentionally kept separate from `Roll35Core.Data.Spell`
  to allow for parallel initialization of the tables, as there are a
  _very_ large number of spells to process.
  """

  use GenServer

  require Logger

  @call_timeout 10_000

  @spec start_link(term()) :: GenServer.on_start()
  def start_link(_) do
    Logger.info("Starting #{__MODULE__}.")

    GenServer.start_link(__MODULE__, [], name: {:via, Registry, {Roll35Core.Registry, :spell_db}})
  end

  @impl GenServer
  def init(_) do
    Process.flag(:trap_exit, true)

    path = Path.join(Application.fetch_env!(:roll35_core, :db_path), "spells.sqlite3")

    {:ok, conn} = Sqlitex.open(path)

    {:ok, %{path: path, conn: conn}}
  end

  @impl GenServer
  def handle_call({:exec, cmd}, _from, state) do
    {:reply, Sqlitex.exec(state.conn, cmd), state}
  end

  @impl GenServer
  def handle_call({:query, query, params}, _from, state) do
    {:reply, Sqlitex.query(state.conn, query, into: %{}, bind: params), state}
  end

  @impl GenServer
  def terminate(_reason, state) do
    Sqlitex.close(state.conn)
  end

  @doc """
  Run a given SQL statement against the database.

  This is a thin veneer over `Sqlitex.exec/3`.
  """
  @spec exec(GenServer.server(), String.t()) :: :ok | Sqlitex.sqlite_error()
  def exec(server, sql) do
    GenServer.call(server, {:exec, sql}, @call_timeout)
  end

  @doc """
  Run a given SQL query against the database.

  This is a thin veneer over `Sqlitex.query/3`.
  """
  @spec query(GenServer.server(), String.t(), list()) ::
          {:ok, [%{atom() => term()}]} | {:error, term()}
  def query(server, sql, bind \\ []) do
    GenServer.call(server, {:query, sql, bind}, @call_timeout)
  end
end
