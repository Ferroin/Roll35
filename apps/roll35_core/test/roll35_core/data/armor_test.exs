defmodule Roll35Core.Data.ArmorTest do
  @moduledoc false
  use Roll35Core.TestHarness.BattleGear, async: true

  alias Roll35Core.Data.Armor
  alias Roll35Core.Types

  alias Roll35Core.TestHarness
  alias Roll35Core.TestHarness.BattleGear

  require TestHarness

  @testfile Path.join("priv", "armor.yaml")
  @testiter 20

  @enchant_range 1..5
  @item_types [:armor, :shield]

  describe "Roll35Core.Data.Armor.load_data/1" do
    setup do
      data = Armor.load_data(@testfile)

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      BattleGear.check_core_data_type("Armor", context)
    end

    test "Returned map has expected keys with expected value types.", context do
      BattleGear.check_core_data_keys("Armor", context)
    end

    test "Tags list has the correct format.", context do
      BattleGear.check_tag_types("Armor", context)
    end

    test "Rank maps have the correct format.", context do
      BattleGear.check_rank_maps("Armor", context)
    end

    test "Base item list has the correct format.", context do
      BattleGear.check_base("Armor", context, @item_types)
    end

    test "Enchantment map has the correct format.", context do
      BattleGear.check_enchantments("Armor", context, @item_types, @enchant_range)
    end

    test "Specific map has the correct format.", context do
      assert MapSet.new(Map.keys(context.data.specific)) == MapSet.new(@item_types),
             "Armor specific item map does not have correct keys (#{
               inspect(Map.keys(context.data.specific))
             })."

      context.data.specific
      |> Task.async_stream(fn {key, map1} ->
        prefix = "Armor specifc item #{key}"

        assert TestHarness.map_has_rank_keys(map1),
               "#{prefix} does not have rank keys (#{inspect(Map.keys(map1))})."

        Enum.each(map1, fn {rank, map2} ->
          prefix = "#{prefix} #{rank}"

          BattleGear.specific_item_subchecks(prefix, map2)
        end)
      end)
      |> Enum.to_list()
    end
  end

  describe "Roll35Core.Data.Armor.tags/1" do
    setup do
      {:ok, server} = start_supervised({Armor, {nil, @testfile}})

      %{server: server}
    end

    test "Properly returns a list of valid tags.", context do
      BattleGear.live_tags_test(Armor, context)
    end
  end

  describe "Roll35Core.Data.Armor.get_base/2" do
    setup do
      {:ok, server} = start_supervised({Armor, {nil, @testfile}})

      %{server: server}
    end

    test "Properly returns a map based on the passed string.", context do
      BattleGear.live_get_base_test(Armor, context, @testiter)
    end
  end

  describe "Roll35Core.Data.Armor.random_base/2" do
    setup do
      {:ok, server} = start_supervised({Armor, {nil, @testfile}})

      %{server: server}
    end

    test "Returns a valid item.", context do
      BattleGear.live_random_base_test(Armor, context, @testiter)
    end

    test "Returns correct items for given tags.", context do
      BattleGear.live_random_base_tags_test(Armor, context, @testiter, @item_types)
    end
  end

  describe "Roll35Core.Data.Armor.random_enchantment/5" do
    setup do
      {:ok, server} = start_supervised({Armor, {nil, @testfile}})

      %{server: server}
    end

    test "Returns correctly formatted enchantments.", context do
      BattleGear.live_random_enchantment_test(
        Armor,
        context,
        @testiter,
        @item_types,
        @enchant_range
      )
    end
  end

  describe "Roll35Core.Data.Armor.random/4" do
    setup do
      {:ok, server} = start_supervised({Armor, {nil, @testfile}})

      %{server: server}
    end

    test "Returns correctly formatted items.", context do
      BattleGear.live_random_test(Armor, context, @testiter, @enchant_range)
    end

    test "Does not return specific items when told not to.", context do
      BattleGear.live_random_nonspecific_test(Armor, context, @testiter)
    end
  end

  describe "Roll35Core.Data.Armor.random_specific/4" do
    setup do
      {:ok, server} = start_supervised({Armor, {nil, @testfile}})

      %{server: server}
    end

    test "Returns items correctly.", context do
      agent = context.server

      Enum.each(1..@testiter, fn _ ->
        type = Enum.random(@item_types)
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())
        item = Armor.random_specific(agent, type, rank, subrank)

        BattleGear.check_specific_item(item)
      end)
    end
  end
end
