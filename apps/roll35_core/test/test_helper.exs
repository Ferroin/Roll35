ExUnit.start()

defmodule Roll35Core.TestHarness do
  defmacro compound_itemlist_tests do
    quote do
      test "Returned data structure is a map.", context do
        assert is_map(context.data)
      end

      test "Returned map has an entry for each rank.", context do
        assert MapSet.equal?(
                 MapSet.new(Map.keys(context.data)),
                 MapSet.new(Roll35Core.Types.ranks())
               )
      end

      test "Returned map’s entries are lists.", context do
        assert Enum.all?(Map.values(context.data), &is_list/1)
      end

      test "Entries of the returned map have the correct format.", context do
        assert Enum.all?(Map.values(context.data), fn entry ->
                 Enum.all?(entry, fn item ->
                   is_integer(item.weight) and item.weight >= 0 and is_map(item.value) and
                     is_binary(item.value.name)
                 end)
               end)
      end
    end
  end
end
