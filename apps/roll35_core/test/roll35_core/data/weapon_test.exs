defmodule Roll35Core.Data.WeaponTest do
  @moduledoc false
  use Roll35Core.TestHarness.BattleGear, async: true

  alias Roll35Core.Data.Weapon
  alias Roll35Core.Types

  alias Roll35Core.TestHarness
  alias Roll35Core.TestHarness.BattleGear

  @testfile Path.join("priv", "weapon.yaml")

  @item_types [:melee, :ranged, :ammo]
  @enchant_range 1..4

  describe "Roll35Core.Data.Weapon.load_data/1" do
    setup do
      data = Weapon.load_data(@testfile)

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      BattleGear.check_core_data_type("Weapon", context)
    end

    test "Returned map has expected keys with expected value types.", context do
      BattleGear.check_core_data_keys("Weapon", context)
    end

    test "Tags list has the correct format.", context do
      BattleGear.check_tag_types("Weapon", context)
    end

    test "Rank maps have the correct format.", context do
      BattleGear.check_rank_maps("Weapon", context)
    end

    test "Base item list has the correct format.", context do
      BattleGear.check_base("Weapon", context, @item_types)
    end

    test "Enchantment map has the correct format.", context do
      BattleGear.check_enchantments("Weapon", context, @item_types, 1..4)
    end

    test "Specific map has the correct format.", context do
      assert TestHarness.map_has_rank_keys(context.data.specific)

      "Weapon specific item map does not have correct keys (#{inspect(Map.keys(context.data.specific))})."

      context.data.specific
      |> Task.async_stream(fn {rank, map} ->
        prefix = "Weapon specifc item #{rank}"

        BattleGear.specific_item_subchecks(prefix, map)
      end)
      |> Enum.to_list()
    end
  end

  describe "Roll35Core.Data.Weapon.tags/1" do
    setup do
      {:ok, server} = start_supervised({Weapon, [name: nil, datapath: @testfile]})

      %{server: server}
    end

    test "Properly returns a list of valid tags.", context do
      BattleGear.live_tags_test(Weapon, context)
    end
  end

  describe "Roll35Core.Data.Weapon.get_base/2" do
    setup do
      {:ok, server} = start_supervised({Weapon, [name: nil, datapath: @testfile]})

      %{server: server}
    end

    test "Properly returns a map based on the passed string.", context do
      BattleGear.live_get_base_test(Weapon, context)
    end
  end

  describe "Roll35Core.Data.Weapon.random_base/2" do
    setup do
      {:ok, server} = start_supervised({Weapon, [name: nil, datapath: @testfile]})

      %{server: server}
    end

    test "Returns a valid item.", context do
      BattleGear.live_random_base_test(Weapon, context)
    end

    test "Returns correct items for given tags.", context do
      BattleGear.live_random_base_tags_test(Weapon, context, @item_types)
    end
  end

  describe "Roll35Core.Data.Weapon.random_enchantment/5" do
    setup do
      {:ok, server} = start_supervised({Weapon, [name: nil, datapath: @testfile]})

      %{server: server}
    end

    test "Returns correctly formatted enchantments.", context do
      BattleGear.live_random_enchantment_test(
        Weapon,
        context,
        @item_types,
        @enchant_range
      )
    end
  end

  describe "Roll35Core.Data.Weapon.random/4" do
    setup do
      {:ok, server} = start_supervised({Weapon, [name: nil, datapath: @testfile]})

      %{server: server}
    end

    test "Returns correctly formatted items.", context do
      BattleGear.live_random_test(Weapon, context, @enchant_range)
    end

    test "Does not return specific items when told not to.", context do
      BattleGear.live_random_nonspecific_test(Weapon, context)
    end
  end

  describe "Roll35Core.Data.Weapon.random_specific/4" do
    setup do
      {:ok, server} = start_supervised({Weapon, [name: nil, datapath: @testfile]})

      %{server: server}
    end

    test "Returns items correctly.", context do
      agent = context.server

      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())
        item = Weapon.random_specific(agent, rank, subrank)

        BattleGear.check_specific_item(item)
      end)
    end
  end
end
