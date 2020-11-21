defmodule Roll35Core.Data.CompoundAgentTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.CompoundAgent

  alias Roll35Core.TestHarness

  @testdata """
  ---
  - {minor: 1, medium: 0, major: 0, name: "Item 1"}
  - {minor: 1, medium: 1, major: 0, name: "Item 2"}
  - {minor: 1, medium: 0, major: 1, name: "Item 3"}
  - {minor: 1, medium: 1, major: 1, name: "Item 4"}
  - {minor: 0, medium: 1, major: 0, name: "Item 5"}
  - {minor: 0, medium: 0, major: 1, name: "Item 6"}
  - {minor: 0, medium: 1, major: 1, name: "Item 7"}
  ...
  """
  @minor_items ["Item 1", "Item 2", "Item 3", "Item 4"]
  @medium_items ["Item 2", "Item 4", "Item 5", "Item 7"]
  @major_items ["Item 3", "Item 4", "Item 6", "Item 7"]
  @all_items (@minor_items ++ @medium_items ++ @major_items) |> Enum.sort() |> Enum.dedup()
  @testfile "compound_agent_test.yaml"
  @testpath Path.join(Application.app_dir(:roll35_core), @testfile)

  setup_all do
    on_exit(fn -> File.rm!(@testpath) end)

    File.write!(@testpath, @testdata, [:sync])
  end

  describe "Roll35Core.Data.CompoundAgent.load_data/1" do
    setup do
      data = CompoundAgent.load_data(@testfile)

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context.data)
    end

    test "Returned map has an entry for each rank.", context do
      assert Roll35Core.TestHarness.map_has_rank_keys(context.data)
    end

    test "Returned map’s entries are lists.", context do
      assert Enum.all?(Map.values(context.data), &is_list/1)
    end

    test "Entries of the returned map have the correct format.", context do
      Enum.each(context.data, fn {_, entry} ->
        Enum.each(entry, fn item ->
          assert is_map(item)
          assert Roll35Core.TestHarness.map_has_weighted_random_keys(item)

          assert is_integer(item.weight)
          assert item.weight >= 0

          assert is_map(item.value)

          assert Map.has_key?(item.value, :name)
          assert String.valid?(item.value.name)
        end)
      end)
    end
  end

  describe "Roll35Core.Data.CompoundAgent.random/1" do
    setup do
      {:ok, server} = start_supervised({CompoundAgent, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid items of a random rank.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = CompoundAgent.random(agent)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @all_items
      end)
    end
  end

  describe "Roll35Core.Data.CompoundAgent.random/2" do
    setup do
      {:ok, server} = start_supervised({CompoundAgent, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid minor items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = CompoundAgent.random(agent, :minor)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @minor_items
      end)
    end

    test "Returns valid medium items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = CompoundAgent.random(agent, :medium)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @medium_items
      end)
    end

    test "Returns valid major items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = CompoundAgent.random(agent, :major)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @major_items
      end)
    end
  end
end
