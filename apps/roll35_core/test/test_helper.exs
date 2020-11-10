ExUnit.start()

defmodule Roll35Core.TestHarness do
  @moduledoc false

  alias Roll35Core.Types

  defmacro compound_itemlist_tests do
    quote do
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

  defmacro ranked_itemlist_tests do
    quote do
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

  defmacro armor_weapon_core_tests(prefix) do
    quote do
      test "Returned data structure is a map.", context do
        assert is_map(context.data), "#{unquote(prefix)} data is not a map."
      end

      test "Returned map has expected keys with expected value types.", context do
        assert Enum.all?(Map.keys(context.data), &is_atom/1),
               "#{unquote(prefix)} data keys are not all atoms."

        assert MapSet.new(Map.keys(context.data)) ==
                 MapSet.new([:base, :specific, :enchantments, :tags | Types.ranks()]),
               "#{unquote(prefix)} data does not contain the correct set of keys (#{
                 inspect(Map.keys(context.data))
               })."

        assert is_list(context.data.base), "#{unquote(prefix)} base item data is not a list."

        assert is_map(context.data.specific),
               "#{unquote(prefix)} specific item data is not a map."

        assert is_map(context.data.enchantments),
               "#{unquote(prefix)} enchantment data is not a map."

        assert Enum.all?(Types.ranks(), fn rank -> is_map(context.data[rank]) end),
               "#{unquote(prefix)} rank entries are not all maps."

        assert is_list(context.data.tags), "#{unquote(prefix)} tag data is not a list."
      end

      test "Tags list has the correct format.", context do
        assert Enum.all?(context.data.tags, &is_atom/1),
               "#{unquote(prefix)} tags are not all atoms."
      end

      test "Rank maps have the correct format.", context do
        Types.ranks()
        |> Task.async_stream(fn rank ->
          data = context.data[rank]

          assert MapSet.new(Map.keys(data)) == MapSet.new(Types.subranks()) or
                   MapSet.new(Map.keys(data)) == MapSet.new(Types.full_subranks()),
                 "#{unquote(prefix)} #{rank} data does not have subrank keys (#{
                   inspect(Map.keys(data))
                 })."

          Enum.each(data, fn {key, value} ->
            assert is_list(value), "#{unquote(prefix)} #{rank} #{key} data is not a list."

            value
            |> Enum.with_index()
            |> Enum.each(fn {item, index} ->
              prefix = "#{unquote(prefix)} #{rank} #{key} item #{index}"
              assert is_map(item), "#{prefix} is not a map."

              assert Roll35Core.TestHarness.map_has_weighted_random_keys(item),
                     "#{prefix} does not have the correct keys (#{inspect(Map.keys(item))})."

              assert is_integer(item.weight), "#{prefix} weight key is not an integer."
              assert item.weight >= 0, "#{prefix} weight key is less than zero."

              assert is_map(item.value), "#{prefix} value key is not a map."

              assert Map.has_key?(item.value, :bonus) or Map.has_key?(item.value, :specific),
                     "#{prefix} value map is missing a bonus or specific key."

              if Map.has_key?(item.value, :bonus) do
                assert is_integer(item.value.bonus),
                       "#{prefix} value map bonus key is not an integer."

                assert item.value.bonus > 0, "#{prefix} value map bonus key is out of range."

                assert Map.has_key?(item.value, :enchants),
                       "#{prefix} value map is missing an enchants key."

                assert is_list(item.value.enchants),
                       "#{prefix} value map enchants key is not a list."

                if length(item.value.enchants) > 0 do
                  item.value.enchants
                  |> Enum.with_index()
                  |> Enum.each(fn {enchant, index} ->
                    assert is_integer(enchant),
                           "#{prefix} value map enchants list item #{index} is not an integer."

                    assert enchant > 0,
                           "#{prefix} value map enchants list item #{index} is out of range."
                  end)
                end
              end

              if Map.has_key?(item.value, :specific) do
                assert is_list(item.value.specific),
                       "#{prefix} value map specific key is not a list."

                assert Enum.all?(item.value.specific, &is_binary/1),
                       "#{prefix} value map specific list not all items are strings."
              end
            end)
          end)
        end)
        |> Enum.to_list()
      end
    end
  end

  defmacro armor_weapon_base_tests(prefix, types) do
    quote do
      test "Base list has the correct format.", context do
        context.data.base
        |> Enum.with_index()
        |> Task.async_stream(fn {entry, index} ->
          prefix = "#{unquote(prefix)} base items entry #{index}"

          assert is_map(entry), "#{prefix} is not a map."

          assert MapSet.subset?(
                   MapSet.new([:name, :cost, :type, :tags]),
                   MapSet.new(Map.keys(entry))
                 )

          "#{prefix} does not have the correct keys (#{inspect(Map.keys(entry))})."

          assert is_binary(entry.name), "#{prefix} name key is not a string."

          assert is_integer(entry.cost) or is_float(entry.cost),
                 "#{prefix} cost key is not a number."

          assert entry.cost >= 0, "#{prefix} cost key is less than zero."

          assert entry.type in unquote(types),
                 "#{prefix} type is invalid (#{inspect(entry.type)})."

          assert is_list(entry.tags), "#{prefix} tags key is not a list."
          assert Enum.all?(entry.tags, &is_atom/1), "#{prefix} tags entries are not all atoms."

          if Map.has_key?(entry, :count) do
            assert is_integer(entry.count), "#{prefix} count is not an integer."
            assert entry.count > 0, "#{prefix} count is not greater than zero."
          end
        end)
        |> Enum.to_list()
      end
    end
  end

  defmacro armor_weapon_enchantment_tests(prefix, types, range) do
    quote do
      test "Enchantment map has the correct format.", context do
        assert MapSet.new(Map.keys(context.data.enchantments)) ==
                 MapSet.new(unquote(types)),
               "#{unquote(prefix)} enchantment map does not have correct keys (#{
                 inspect(Map.keys(context.data.enchantments))
               })."

        context.data.enchantments
        |> Task.async_stream(fn {key, map1} ->
          prefix = "#{unquote(prefix)} enchantment #{key}"

          assert MapSet.equal?(MapSet.new(Map.keys(map1)), MapSet.new(unquote(range))),
                 "#{prefix} does not have the correct keys (#{inspect(Map.keys(map1))})."

          Enum.each(map1, fn {level, level_items} ->
            prefix = "#{prefix} #{level}"

            assert is_list(level_items), "#{prefix} is not a list."

            level_items
            |> Enum.with_index()
            |> Enum.each(fn {item, index} ->
              prefix = "#{prefix} item #{index}"

              assert is_map(item), "#{prefix} is not a map."

              assert Roll35Core.TestHarness.map_has_weighted_random_keys(item),
                     "#{prefix} does not have the correct keys (#{inspect(Map.keys(item))})."

              assert MapSet.subset?(
                       MapSet.new(Map.keys(item.value)),
                       MapSet.new([:name, :cost, :limit, :exclude, :remove, :add])
                     ),
                     "#{prefix} value map does not have the correct keys (#{
                       inspect(Map.keys(item.value))
                     })."

              assert Map.has_key?(item.value, :name), "#{prefix} value map is missing name key."
              assert is_binary(item.value.name), "#{prefix} value map name key is not a string."

              if Map.has_key?(item.value, :cost) do
                assert is_integer(item.value.cost) or is_float(item.value.cost),
                       "#{prefix} value map cost key is not a number."

                assert item.value.cost >= 0, "#{prefix} value map cost key is below zero."
              end

              if Map.has_key?(item.value, :add) do
                assert is_list(item.value.add), "#{prefix} value map add key is not a list."

                assert Enum.all?(item.value.add, &is_atom/1),
                       "##{prefix} value map add list entries are not all atoms."
              end

              if Map.has_key?(item.value, :remove) do
                assert is_list(item.value.remove), "#{prefix} value map remove key is not a list."

                assert Enum.all?(item.value.remove, &is_atom/1),
                       "##{prefix} value map remove list entries are not all atoms."
              end

              if Map.has_key?(item.value, :limit) do
                assert is_map(item.value.limit), "#{prefix} value map limit key is not a map."

                assert MapSet.new(Map.keys(item.value.limit)) in [
                         MapSet.new([:only]),
                         MapSet.new([:not])
                       ],
                       "#{prefix} value map limit map has an invalid set of keys (#{
                         inspect(Map.keys(item.value.limit))
                       })."

                if Map.has_key?(item.value.limit, :only) do
                  assert Enum.all?(item.value.limit.only, &is_atom/1),
                         "#{prefix} value map limit map only key entries are not all atoms."
                end

                if Map.has_key?(item.value.limit, :not) do
                  assert Enum.all?(item.value.limit.not, &is_atom/1),
                         "#{prefix} value map limit map not key entries are not all atoms."
                end
              end

              if Map.has_key?(item.value, :exclude) do
                assert is_list(item.value.exclude),
                       "#{prefix} value map exclude key is not a list."

                assert Enum.all?(item.value.exclude, &is_binary/1),
                       "#{prefix} value map limit list contains values that are not strings."
              end
            end)
          end)
        end)
        |> Enum.to_list()
      end
    end
  end

  defmacro armor_weapon_specific_subtests(prefix, data) do
    quote do
      assert Roll35Core.TestHarness.map_has_subrank_keys(unquote(data)),
             "#{unquote(prefix)} does not have subrank keys (#{inspect(Map.keys(unquote(data)))})."

      Enum.each(unquote(data), fn {subrank, entry} ->
        prefix = "#{unquote(prefix)} #{subrank}"
        assert is_list(entry), "#{prefix} is not a list."

        entry
        |> Enum.with_index()
        |> Enum.each(fn {item, index} ->
          prefix = "#{prefix} item #{index}"

          assert is_map(item), "#{prefix} is not a map."

          assert Roll35Core.TestHarness.map_has_weighted_random_keys(item),
                 "#{prefix} does not have correct keys (#{inspect(Map.keys(item))})."

          assert is_integer(item.weight), "#{prefix} weight key is not an integer."
          assert item.weight >= 0, "#{prefix} weight key is less than zero."

          assert is_map(item.value), "#{prefix} value key is not a map."

          assert MapSet.equal?(MapSet.new(Map.keys(item.value)), MapSet.new([:name, :cost])),
                 "#{prefix} value map does not have correct keys (#{inspect(Map.keys(item.value))})."
        end)
      end)
    end
  end

  @spec map_has_weighted_random_keys(map()) :: bool()
  def map_has_weighted_random_keys(map) do
    MapSet.equal?(MapSet.new(Map.keys(map)), MapSet.new([:weight, :value]))
  end

  @spec map_has_rank_keys(map()) :: bool()
  def map_has_rank_keys(map) do
    MapSet.equal?(MapSet.new(Map.keys(map)), MapSet.new(Roll35Core.Types.ranks())) or
      MapSet.equal?(MapSet.new(Map.keys(map)), MapSet.new(Roll35Core.Types.limited_ranks()))
  end

  @spec map_has_subrank_keys(map()) :: bool()
  def map_has_subrank_keys(map) do
    MapSet.equal?(MapSet.new(Map.keys(map)), MapSet.new(Roll35Core.Types.subranks())) or
      MapSet.equal?(MapSet.new(Map.keys(map)), MapSet.new(Roll35Core.Types.full_subranks()))
  end
end
