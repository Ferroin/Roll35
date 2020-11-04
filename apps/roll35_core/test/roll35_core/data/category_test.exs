defmodule Roll35Core.Data.CategoryTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Category
  alias Roll35Core.Types

  describe "Roll35Core.Data.Category.load_data/0" do
    setup do
      data = Category.load_data()

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context[:data])
    end

    test "Returned map has an entry for each rank.", context do
      assert MapSet.equal?(
               MapSet.new(Map.keys(context[:data])),
               MapSet.new(Types.ranks())
             )
    end

    test "Returned map’s entries are lists.", context do
      assert Enum.all?(Map.values(context[:data]), &is_list/1)
    end

    test "Entries of the returned map have the correct format.", context do
      assert Enum.all?(Map.values(context[:data]), fn entry ->
               Enum.all?(entry, fn item ->
                 is_integer(item[:weight]) and item[:weight] > 0 and is_atom(item[:value]) and
                   item[:value] in Types.categories()
               end)
             end)
    end
  end
end
