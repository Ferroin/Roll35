defmodule Roll35Core.Data.CompoundAgentTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.CompoundAgent

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
  # @minor_items ["Item 1", "Item 2", "Item 3", "Item 4"]
  # @medium_items ["Item 2", "Item 4", "Item 5", "Item 7"]
  # @major_items ["Item 3", "Item 4", "Item 6", "Item 7"]
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

          assert Map.has_key?(item, :weight)
          assert is_integer(item.weight)
          assert item.weight >= 0

          assert Map.has_key?(item, :value)
          assert is_map(item.value)

          assert Map.has_key?(item.value, :name)
          assert is_binary(item.value.name)
        end)
      end)
    end
  end
end
