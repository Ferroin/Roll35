defmodule Roll35Core.Data.RankedAgentTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.RankedAgent

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

            assert Map.has_key?(item, :weight)
            assert is_integer(item.weight)
            assert item.weight >= 0

            assert Map.has_key?(item, :value)
            assert is_map(item.value)

            assert Map.has_key?(item.value, :name) or Map.has_key?(item.value, :reroll)

            if Map.has_key?(item.value, :name) do
              assert is_binary(item.value.name)
            end

            if Map.has_key?(item.value, :reroll) do
              assert is_list(item.value.reroll)

              assert Enum.all?(item.value.reroll, &is_binary/1)
            end
          end)
        end)
      end)
    end
  end
end
