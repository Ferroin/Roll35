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

  defmacro ranked_itemlist_tests do
    quote do
      test "Returned data structure is a map.", context do
        assert is_map(context.data)
      end

      test "Returned map has an entry for each rank.", context do
        assert MapSet.equal?(
                 MapSet.new(Map.keys(context.data)),
                 MapSet.new(Roll35Core.Types.ranks())
               ) or
                 MapSet.equal?(
                   MapSet.new(Map.keys(context.data)),
                   MapSet.new(Roll35Core.Types.limited_ranks())
                 )
      end

      test "Returned map’s entries are maps.", context do
        assert Enum.all?(Map.values(context.data), &is_map/1)
      end

      test "Returned map’s entries have entries for each sub-rank.", context do
        Enum.each(context.data, fn {_, value} ->
          assert MapSet.equal?(
                   MapSet.new(Map.keys(value)),
                   MapSet.new(Roll35Core.Types.subranks())
                 ) or
                   MapSet.equal?(
                     MapSet.new(Map.keys(value)),
                     MapSet.new(Roll35Core.Types.full_subranks())
                   )
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
                assert is_binary(item.value.reroll)
              end
            end)
          end)
        end)
      end
    end
  end
end
