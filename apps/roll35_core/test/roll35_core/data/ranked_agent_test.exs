defmodule Roll35Core.Data.RankedAgentTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.RankedAgent

  alias Roll35Core.TestHarness

  @testdata """
  ---
  minor:
    least:
      - {weight: 1, name: "Item 1"}
      - {weight: 1, name: "Item 2"}
    lesser:
      - {weight: 1, name: "Item 3"}
    greater:
      - {weight: 1, name: "Item 4"}
  medium:
    lesser:
      - {weight: 1, name: "Item 5"}
    greater:
      - {weight: 1, name: "Item 6"}
  major:
    lesser:
      - {weight: 1, name: "Item 7"}
    greater:
      - {weight: 1, name: "Item 8"}
  ...
  """
  @minor_least_items ["Item 1", "Item 2"]
  @minor_lesser_items ["Item 3"]
  @minor_greater_items ["Item 4"]
  @minor_items @minor_least_items ++ @minor_lesser_items ++ @minor_greater_items
  @medium_lesser_items ["Item 5"]
  @medium_greater_items ["Item 6"]
  @medium_items @medium_lesser_items ++ @medium_greater_items
  @major_lesser_items ["Item 7"]
  @major_greater_items ["Item 8"]
  @major_items @major_lesser_items ++ @major_greater_items
  @all_items @minor_items ++ @medium_items ++ @major_items
  @testfile "ranked_agent_test.yaml"
  @testpath Path.join(Application.app_dir(:roll35_core), @testfile)

  setup_all do
    on_exit(fn -> File.rm!(@testpath) end)

    File.write!(@testpath, @testdata, [:sync])
  end

  describe "Roll35Core.Data.RankedAgent.load_data/1" do
    setup do
      data = RankedAgent.load_data(@testfile)

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context.data)
    end

    test "Returned map has an entry for each rank.", context do
      assert Roll35Core.TestHarness.map_has_rank_keys(context.data)
    end

    test "Returned map’s entries are maps.", context do
      assert Enum.all?(Map.values(context.data), &is_map/1)
    end

    test "Returned map’s entries have entries for each sub-rank.", context do
      Enum.each(context.data, fn {_, value} ->
        assert Roll35Core.TestHarness.map_has_subrank_keys(value)
      end)
    end

    test "Entries of the returned map have the correct format.", context do
      Enum.each(context.data, fn {_, rank} ->
        Enum.each(rank, fn {_, subrank} ->
          Enum.each(subrank, fn item ->
            assert is_map(item)
            assert Roll35Core.TestHarness.map_has_weighted_random_keys(item)

            assert is_integer(item.weight)
            assert item.weight >= 0

            assert is_map(item.value)

            assert Map.has_key?(item.value, :name) or Map.has_key?(item.value, :reroll)

            if Map.has_key?(item.value, :name) do
              assert String.valid?(item.value.name)
            end

            if Map.has_key?(item.value, :reroll) do
              assert is_list(item.value.reroll)

              assert Enum.all?(item.value.reroll, &String.valid?/1)
            end
          end)
        end)
      end)
    end
  end

  describe "Roll35Core.Data.RankedAgent.random/1" do
    setup do
      {:ok, server} = start_supervised({RankedAgent, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid items of a random rank.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @all_items
      end)
    end
  end

  describe "Roll35Core.Data.RankedAgent.random/2" do
    setup do
      {:ok, server} = start_supervised({RankedAgent, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid minor items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :minor)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @minor_items
      end)
    end

    test "Returns valid medium items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :medium)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @medium_items
      end)
    end

    test "Returns valid major items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :major)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @major_items
      end)
    end
  end

  describe "Roll35Core.Data.RankedAgent.random/3" do
    setup do
      {:ok, server} = start_supervised({RankedAgent, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid minor least items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :minor, :least)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @minor_least_items
      end)
    end

    test "Returns valid minor lesser items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :minor, :lesser)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @minor_lesser_items
      end)
    end

    test "Returns valid minor greater items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :minor, :greater)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @minor_greater_items
      end)
    end

    test "Returns valid medium lesser items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :medium, :lesser)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @medium_lesser_items
      end)
    end

    test "Returns valid medium greater items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :medium, :greater)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @medium_greater_items
      end)
    end

    test "Returns valid major lesser items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :major, :lesser)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @major_lesser_items
      end)
    end

    test "Returns valid major greater items.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        item = RankedAgent.random(agent, :major, :greater)

        assert is_map(item)
        assert Map.has_key?(item, :name)
        assert String.valid?(item.name)
        assert item.name in @major_greater_items
      end)
    end
  end
end
