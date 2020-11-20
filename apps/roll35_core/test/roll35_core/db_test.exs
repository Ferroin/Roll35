defmodule Roll35Core.DBTest do
  use ExUnit.Case, async: true

  alias Roll35Core.DB

  @test_db_path Path.join('.', 'db_test.sqlite3')

  setup_all do
    on_exit(fn -> File.rm!(@test_db_path) end)

    db = start_supervised!({DB, @test_db_path})

    %{db: db}
  end

  defp sqlite_cmd(sql) do
    System.cmd("sqlite3", [@test_db_path, sql], stderr_to_stdout: true, env: [])
  end

  test "Roll35Core.DB.exec/2", context do
    db = context.db

    assert {:error, _} = DB.exec(db, "not really sql...")

    assert :ok = DB.exec(db, "CREATE TABLE exec_test(id INTEGER, foo INTEGER, bar TEXT);")

    assert {"exec_test\n", 0} =
             sqlite_cmd("SELECT name FROM sqlite_master WHERE type='table' AND name='exec_test';")

    assert :ok = DB.exec(db, "INSERT INTO exec_test (id, foo, bar) VALUES (0, 1, 'test');")

    assert {"0|1|test\n", 0} = sqlite_cmd("SELECT * FROM exec_test WHERE id='0';")

    assert :ok = DB.exec(db, "DROP TABLE exec_test;")

    assert {"Error: no such table: exec_test\n", 1} =
             sqlite_cmd("SELECT * FROM exec_test WHERE id='0';")
  end

  test "Roll35Core.DB.query/3", context do
    db = context.db

    assert :ok = DB.exec(db, "CREATE TABLE query_test(id INTEGER, foo INTEGER, bar TEXT);")

    assert {:ok, []} = DB.query(db, "SELECT * FROM query_test WHERE id='0';")

    assert :ok = DB.exec(db, "INSERT INTO query_test (id, foo, bar) VALUES (0, 1, 'test');")

    assert {:ok, [%{id: 0, foo: 1, bar: "test"}]} =
             DB.query(db, "SELECT * FROM query_test WHERE id='0';")
  end
end
