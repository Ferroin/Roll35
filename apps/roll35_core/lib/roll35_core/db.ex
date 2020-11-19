defmodule Roll35Core.DB do
  @moduledoc """
  A GenServer for handling access to an SQLite database.

  This exists because Sqlitex.Server doesn’t provide a way to run
  arbirary SQL scripts against databases.
  """

  use GenServer

  require Logger

  @call_timeout 10_000

  @spec start_link(term()) :: GenServer.on_start()
  def start_link([name, path]) do
    Logger.info("Starting #{__MODULE__}.")

    GenServer.start_link(__MODULE__, path, name: {:via, Registry, {Roll35Core.Registry, name}})
  end

  @impl GenServer
  def init(path) do
    Process.flag(:trap_exit, true)

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
