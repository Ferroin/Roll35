Logger.configure(level: :warn)

Application.load(:roll35_core)

ExUnit.start()

defmodule Roll35Core.TestHarness do
  @moduledoc false

  @spec iter :: pos_integer()
  def iter, do: 1..10_000

  @spec iter_slow :: pos_integer()
  def iter_slow, do: 1..200

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

defmodule Roll35Core.TestHarness.BattleGear do
  use ExUnit.CaseTemplate

  alias Roll35Core.Types

  alias Roll35Core.TestHarness

  @spec check_specific_item(map()) :: nil
  def check_specific_item(item) do
    assert is_map(item)

    assert Map.has_key?(item, :name)
    assert String.valid?(item.name)

    assert Map.has_key?(item, :cost)
    assert is_integer(item.cost) or String.valid?(item.cost)
  end

  @spec check_core_data_type(String.t(), map()) :: nil
  def check_core_data_type(prefix, ctx) do
    assert is_map(ctx.data), "#{prefix} data is not a map."
  end

  @spec check_core_data_keys(String.t(), map()) :: nil
  def check_core_data_keys(prefix, ctx) do
    assert Enum.all?(Map.keys(ctx.data), &is_atom/1),
           "#{prefix} data keys are not all atoms."

    assert MapSet.new(Map.keys(ctx.data)) ==
             MapSet.new([:base, :specific, :enchantments, :tags | Types.ranks()]),
           "#{prefix} data does not contain the correct set of keys (#{inspect(Map.keys(ctx.data))})."

    assert is_list(ctx.data.base), "#{prefix} base item data is not a list."

    assert is_map(ctx.data.specific), "#{prefix} specific item data is not a map."

    assert is_map(ctx.data.enchantments), "#{prefix} enchantment data is not a map."

    assert Enum.all?(Types.ranks(), fn rank -> is_map(ctx.data[rank]) end),
           "#{prefix} rank entries are not all maps."

    assert is_list(ctx.data.tags), "#{prefix} tag data is not a list."
  end

  @spec check_tag_types(String.t(), map()) :: nil
  def check_tag_types(prefix, ctx) do
    assert Enum.all?(ctx.data.tags, &is_atom/1), "#{prefix} tags are not all atoms."
  end

  @spec check_rank_maps(String.t(), map()) :: nil
  def check_rank_maps(prefix, ctx) do
    Types.ranks()
    |> Task.async_stream(fn rank ->
      data = ctx.data[rank]

      assert MapSet.new(Map.keys(data)) == MapSet.new(Types.subranks()) or
               MapSet.new(Map.keys(data)) == MapSet.new(Types.full_subranks()),
             "#{prefix} #{rank} data does not have subrank keys (#{inspect(Map.keys(data))})."

      Enum.each(data, fn {key, value} ->
        assert is_list(value), "#{prefix} #{rank} #{key} data is not a list."

        value
        |> Enum.with_index()
        |> Enum.each(fn {item, index} ->
          prefix = "#{prefix} #{rank} #{key} item #{index}"
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

            assert Enum.all?(item.value.specific, &String.valid?/1),
                   "#{prefix} value map specific list not all items are strings."
          end
        end)
      end)
    end)
    |> Enum.to_list()
  end

  @spec check_base(String.t(), map(), [atom(), ...]) :: nil
  def check_base(prefix, ctx, types) do
    ctx.data.base
    |> Enum.with_index()
    |> Task.async_stream(fn {entry, index} ->
      prefix = "#{prefix} base items entry #{index}"

      assert is_map(entry), "#{prefix} is not a map."

      assert MapSet.subset?(
               MapSet.new([:name, :cost, :type, :tags]),
               MapSet.new(Map.keys(entry))
             )

      "#{prefix} does not have the correct keys (#{inspect(Map.keys(entry))})."

      assert String.valid?(entry.name), "#{prefix} name key is not a string."

      assert is_integer(entry.cost) or is_float(entry.cost),
             "#{prefix} cost key is not a number."

      assert entry.cost >= 0, "#{prefix} cost key is less than zero."

      assert entry.type in types,
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

  @spec check_enchantments(String.t(), map(), [atom(), ...], Range.t()) :: nil
  def check_enchantments(prefix, ctx, types, range) do
    assert MapSet.new(Map.keys(ctx.data.enchantments)) ==
             MapSet.new(types),
           "#{prefix} enchantment map does not have correct keys (#{inspect(Map.keys(ctx.data.enchantments))})."

    ctx.data.enchantments
    |> Task.async_stream(fn {key, map1} ->
      prefix = "#{prefix} enchantment #{key}"

      assert MapSet.equal?(MapSet.new(Map.keys(map1)), MapSet.new(range)),
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
                 "#{prefix} value map does not have the correct keys (#{inspect(Map.keys(item.value))})."

          assert Map.has_key?(item.value, :name), "#{prefix} value map is missing name key."
          assert String.valid?(item.value.name), "#{prefix} value map name key is not a string."

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
                   "#{prefix} value map limit map has an invalid set of keys (#{inspect(Map.keys(item.value.limit))})."

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

            assert Enum.all?(item.value.exclude, &String.valid?/1),
                   "#{prefix} value map limit list contains values that are not strings."
          end
        end)
      end)
    end)
    |> Enum.to_list()
  end

  @spec specific_item_subchecks(String.t(), map()) :: nil
  def specific_item_subchecks(prefix, data) do
    assert Roll35Core.TestHarness.map_has_subrank_keys(data),
           "#{prefix} does not have subrank keys (#{inspect(Map.keys(data))})."

    Enum.each(data, fn {subrank, entry} ->
      prefix = "#{prefix} #{subrank}"
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

  @spec live_tags_test(module(), map()) :: nil
  def live_tags_test(module, ctx) do
    agent = ctx.server

    tags = module.tags(agent)

    assert is_list(tags)
    assert Enum.all?(tags, &is_atom/1)
  end

  @spec live_get_base_test(module(), map()) :: nil
  def live_get_base_test(module, ctx) do
    agent = ctx.server

    Enum.each(TestHarness.iter(), fn _ ->
      base1 = module.random_base(agent)

      {:ok, base2} = module.get_base(agent, base1.name)

      assert base1 == base2
    end)
  end

  @spec live_random_base_test(module(), map()) :: nil
  def live_random_base_test(module, ctx) do
    agent = ctx.server

    Enum.each(TestHarness.iter(), fn _ ->
      item = module.random_base(agent)

      assert is_map(item)

      assert Map.has_key?(item, :name)
      assert String.valid?(item.name)

      assert Map.has_key?(item, :cost)
      assert is_integer(item.cost) or is_float(item.cost)
    end)
  end

  @spec live_random_base_tags_test(module(), map(), [atom()]) :: nil
  def live_random_base_tags_test(module, ctx, types) do
    agent = ctx.server
    tags = module.tags(agent) ++ types

    Enum.each(TestHarness.iter(), fn _ ->
      tag = Enum.random(tags)

      item = module.random_base(agent, [tag])

      assert tag == item.type or tag in item.tags
    end)
  end

  @spec live_random_enchantment_test(module(), map(), [atom()], Range.t()) :: nil
  def live_random_enchantment_test(module, ctx, types, enchant_range) do
    agent = ctx.server

    Enum.each(TestHarness.iter(), fn _ ->
      type = Enum.random(types)
      bonus = Enum.random(enchant_range)
      item = module.random_enchantment(agent, type, bonus)

      assert is_map(item)

      assert Map.has_key?(item, :name)
      assert String.valid?(item.name)

      if Map.has_key?(item, :cost) do
        assert is_integer(item.cost)
        assert item.cost > 0
      end
    end)
  end

  @spec live_random_test(module(), map(), Range.t()) :: nil
  def live_random_test(module, ctx, enchant_range) do
    agent = ctx.server

    Enum.each(TestHarness.iter(), fn _ ->
      rank = Enum.random(Types.ranks())
      subrank = Enum.random(Types.subranks())
      item = module.random(agent, rank, subrank)

      if Map.has_key?(item, :specific) do
        assert MapSet.equal?(MapSet.new(Map.keys(item)), MapSet.new([:specific]))

        assert is_list(item.specific)

        # TODO: This should be more thorough, only certain sequences of strings are valid.
        assert Enum.all?(item.specific, &String.valid?/1)
      else
        assert MapSet.equal?(MapSet.new(Map.keys(item)), MapSet.new([:bonus, :enchants]))

        assert is_integer(item.bonus)
        assert item.bonus in 1..5

        assert is_list(item.enchants)

        assert Enum.all?(item.enchants, fn i ->
                 is_integer(i) and i in enchant_range
               end)
      end
    end)
  end

  @spec live_random_nonspecific_test(module(), map()) :: nil
  def live_random_nonspecific_test(module, ctx) do
    agent = ctx.server

    Enum.each(TestHarness.iter(), fn _ ->
      rank = Enum.random(Types.ranks())
      subrank = Enum.random(Types.subranks())
      item = module.random(agent, rank, subrank, no_specific: true)

      assert is_map(item)
      refute Map.has_key?(item, :specific)
    end)
  end
end
