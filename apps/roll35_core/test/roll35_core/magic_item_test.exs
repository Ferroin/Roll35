defmodule Roll35Core.MagicItemTest do
  @moduledoc false
  use ExUnit.Case

  alias Roll35Core.Data.Armor
  alias Roll35Core.Data.Spell
  alias Roll35Core.Data.Weapon
  alias Roll35Core.MagicItem
  alias Roll35Core.Types

  alias Roll35Core.TestHarness

  setup_all do
    on_exit(fn -> Application.stop(:roll35_core) end)

    {:ok, _} = Application.ensure_all_started(:roll35_core)

    :ok
  end

  defp valid_item_check({:ok, item}) do
    assert is_map(item)
    assert Map.has_key?(item, :name)
    assert String.valid?(item.name)

    if Map.has_key?(item, :cost) do
      assert is_integer(item.cost) or is_float(item.cost) or item.cost == "varies"
    end

    if Regex.match?(~r/^.*<%= spell %>.*$/, item.name) do
      assert Map.has_key?(item, :spell)
      assert is_map(item.spell)
      assert Map.has_key?(item.spell, :level)
      assert is_integer(item.spell.level)
      assert item.spell.level in 0..9

      if Map.has_key?(item.spell, :cls) do
        assert is_atom(item.spell.cls) or
                 item.spell.cls in [
                   "random",
                   "minimum",
                   "spellpage",
                   "spellpage_arcane",
                   "spellpage_divine"
                 ]
      end
    else
      refute Map.has_key?(item, :spell)
    end
  end

  defp valid_item_check(ret) do
    flunk("Got invalid return value #{inspect(ret)}.")
  end

  describe "Roll35Core.MagicItem.reroll/1" do
    test "Properly returns results for category/rank/subrank sets." do
      Enum.each(TestHarness.iter(), fn _ ->
        category = Enum.random(Types.categories())
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.full_subranks())

        {status1, item1} = MagicItem.reroll([category, rank, subrank])
        {status2, item2} = MagicItem.roll(rank, subrank, category)

        assert status1 == status2,
               "Status mismatch for #{inspect({category, rank, subrank})}, got {#{inspect(status1)}, #{inspect(item1)}} and {#{inspect(status2)}, #{inspect(item2)}}."
      end)
    end

    test "Properly returns results for rank/subrank/slot sets." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.full_subranks())
        slot = Enum.random(Types.slots())

        {status1, item1} = MagicItem.reroll([:wondrous, slot, rank, subrank])
        {status2, item2} = MagicItem.roll(rank, subrank, :wondrous, slot: slot)

        assert status1 == status2,
               "Status mismatch for #{inspect({rank, subrank, slot})}, got {#{inspect(status1)}, #{inspect(item1)}} and {#{inspect(status2)}, #{inspect(item2)}}."
      end)
    end
  end

  describe "Roll35Core.MagicItem.assemble_magic_item/6" do
    test "Returns proper results for armor." do
      Enum.each(TestHarness.iter_slow(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())

        pattern =
          Armor.random({:via, Registry, {Roll35Core.Registry, :armor}}, rank, subrank,
            no_specific: true
          )

        base = Armor.random_base({:via, Registry, {Roll35Core.Registry, :armor}})

        case MagicItem.assemble_magic_item(:armor, pattern, base, 1000, 150) do
          {:ok, item} ->
            assert is_map(item)
            assert MapSet.equal?(MapSet.new(Map.keys(item)), MapSet.new([:name, :cost]))
            assert String.valid?(item.name)
            assert is_integer(item.cost) or is_float(item.cost)
            assert item.cost > 0

          {:error, msg} ->
            assert String.valid?(msg)

          ret ->
            flunk("Got invalid return value #{inspect(ret)}.")
        end
      end)
    end

    test "Returns proper results for weapons." do
      Enum.each(TestHarness.iter_slow(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())

        pattern =
          Weapon.random({:via, Registry, {Roll35Core.Registry, :weapon}}, rank, subrank,
            no_specific: true
          )

        base = Weapon.random_base({:via, Registry, {Roll35Core.Registry, :weapon}})

        {mult, masterwork} =
          if :double in base.tags do
            {4000, 600}
          else
            {2000, 300}
          end

        case MagicItem.assemble_magic_item(:weapon, pattern, base, mult, masterwork) do
          {:ok, item} ->
            assert is_map(item)
            assert MapSet.equal?(MapSet.new(Map.keys(item)), MapSet.new([:name, :cost]))
            assert String.valid?(item.name)
            assert is_integer(item.cost) or is_float(item.cost) or item.cost == "varies"

          {:error, msg} ->
            assert String.valid?(msg)

          ret ->
            flunk("Got invalid return value #{inspect(ret)}.")
        end
      end)
    end
  end

  describe "Roll35Core.MagicItem.roll/4" do
    test "Properly rejects invalid arguments." do
      assert {:error, _} = MagicItem.roll(:minor, :least, :wondrous)
      assert {:error, _} = MagicItem.roll(:minor, :least, nil)
      assert {:error, _} = MagicItem.roll(:minor, :lesser, :rod)
      assert {:error, _} = MagicItem.roll(:minor, :lesser, :staff)
      assert {:error, _} = MagicItem.roll(:minor, nil, :scroll, class: :bogus)
      assert {:error, _} = MagicItem.roll(:minor, nil, :wand, class: :bogus)
      assert {:error, _} = MagicItem.roll(nil, nil, nil)
    end

    test "Returns proper results for wondrous items with specific slot." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())
        slot = Enum.random(Types.slots())

        valid_item_check(MagicItem.roll(rank, subrank, :wondrous, slot: slot))
      end)
    end

    test "Returns proper results for wondrous items without a specific slot." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())

        valid_item_check(MagicItem.roll(rank, subrank, :wondrous))
      end)
    end

    test "Returns proper results for armor and weapons when a base item is specified." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())
        category = Enum.random([:armor, :weapon])

        base =
          if category == :armor do
            Armor.random_base({:via, Registry, {Roll35Core.Registry, :armor}})
          else
            Weapon.random_base({:via, Registry, {Roll35Core.Registry, :weapon}})
          end

        valid_item_check(MagicItem.roll(rank, subrank, category, base: base.name))
      end)
    end

    test "Returns proper results for armor and weapons." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())
        category = Enum.random([:armor, :weapon])

        valid_item_check(MagicItem.roll(rank, subrank, category))
      end)
    end

    test "Returns proper results for scrolls when a class is specified." do
      classes = Spell.get_classes({:via, Registry, {Roll35Core.Registry, :spell}})

      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        category = Enum.random([:scroll, :wand])
        class = Enum.random(classes)

        valid_item_check(MagicItem.roll(rank, nil, category, class: class))
      end)
    end

    test "Returns proper results for compound categories." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())
        category = Enum.random([:potion, :scroll, :wand])

        valid_item_check(MagicItem.roll(rank, subrank, category))
      end)
    end

    test "Returns proper results for ranked categories." do
      Enum.each(TestHarness.iter(), fn _ ->
        category = Enum.random([:ring, :rod, :staff])

        rank =
          if category in [:rod, :staff] do
            Enum.random(Types.limited_ranks())
          else
            Enum.random(Types.ranks())
          end

        subrank = Enum.random(Types.subranks())

        valid_item_check(MagicItem.roll(rank, subrank, category))
      end)
    end

    test "Returns proper results with no category specified." do
      Enum.each(TestHarness.iter(), fn _ ->
        rank = Enum.random(Types.ranks())
        subrank = Enum.random(Types.subranks())

        valid_item_check(MagicItem.roll(rank, subrank, nil))
      end)
    end
  end
end
