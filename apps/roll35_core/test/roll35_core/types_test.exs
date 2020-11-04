defmodule Roll35Core.TypesTest do
  use ExUnit.Case, async: true

  require Roll35Core.Types

  describe "Roll35Core.Types.category" do
    test "All valid values are atoms." do
      assert Enum.all?(Roll35Core.Types.categories(), fn
               item when is_atom(item) -> true
               item when not is_atom(item) -> false
             end)
    end

    test "Guard recognizes all valid values." do
      assert Enum.all?(Roll35Core.Types.categories(), fn
               item when Roll35Core.Types.is_category(item) -> true
               item when not Roll35Core.Types.is_category(item) -> false
             end)
    end

    test "Guard rejects invalid values." do
      refute Enum.any?([nil, "", false], fn
               item when Roll35Core.Types.is_category(item) -> true
               item when not Roll35Core.Types.is_category(item) -> false
             end)
    end
  end

  describe "Roll35Core.Types.rank" do
    test "All valid values are atoms." do
      assert Enum.all?(Roll35Core.Types.ranks(), fn
               item when is_atom(item) -> true
               item when not is_atom(item) -> false
             end)
    end

    test "Guard recognizes all valid values." do
      assert Enum.all?(Roll35Core.Types.ranks(), fn
               item when Roll35Core.Types.is_rank(item) -> true
               item when not Roll35Core.Types.is_rank(item) -> false
             end)
    end

    test "Guard rejects invalid values." do
      refute Enum.any?([nil, "", false], fn
               item when Roll35Core.Types.is_rank(item) -> true
               item when not Roll35Core.Types.is_rank(item) -> false
             end)
    end
  end

  describe "Roll35Core.Types.limited_rank" do
    test "All valid values are atoms." do
      assert Enum.all?(Roll35Core.Types.limited_ranks(), fn
               item when is_atom(item) -> true
               item when not is_atom(item) -> false
             end)
    end

    test "Guard recognizes all valid values." do
      assert Enum.all?(Roll35Core.Types.limited_ranks(), fn
               item when Roll35Core.Types.is_limited_rank(item) -> true
               item when not Roll35Core.Types.is_limited_rank(item) -> false
             end)
    end

    test "Guard rejects invalid values." do
      refute Enum.any?([nil, "", false], fn
               item when Roll35Core.Types.is_limited_rank(item) -> true
               item when not Roll35Core.Types.is_limited_rank(item) -> false
             end)
    end
  end

  describe "Roll35Core.Types.subrank" do
    test "All valid values are atoms." do
      assert Enum.all?(Roll35Core.Types.subranks(), fn
               item when is_atom(item) -> true
               item when not is_atom(item) -> false
             end)
    end

    test "Guard recognizes all valid values." do
      assert Enum.all?(Roll35Core.Types.subranks(), fn
               item when Roll35Core.Types.is_subrank(item) -> true
               item when not Roll35Core.Types.is_subrank(item) -> false
             end)
    end

    test "Guard rejects invalid values." do
      refute Enum.any?([nil, "", false], fn
               item when Roll35Core.Types.is_subrank(item) -> true
               item when not Roll35Core.Types.is_subrank(item) -> false
             end)
    end
  end

  describe "Roll35Core.Types.full_subrank" do
    test "All valid values are atoms." do
      assert Enum.all?(Roll35Core.Types.full_subranks(), fn
               item when is_atom(item) -> true
               item when not is_atom(item) -> false
             end)
    end

    test "Guard recognizes all valid values." do
      assert Enum.all?(Roll35Core.Types.full_subranks(), fn
               item when Roll35Core.Types.is_full_subrank(item) -> true
               item when not Roll35Core.Types.is_full_subrank(item) -> false
             end)
    end

    test "Guard rejects invalid values." do
      refute Enum.any?([nil, "", false], fn
               item when Roll35Core.Types.is_full_subrank(item) -> true
               item when not Roll35Core.Types.is_full_subrank(item) -> false
             end)
    end
  end

  describe "Roll35Core.Types.slot" do
    test "All valid values are atoms." do
      assert Enum.all?(Roll35Core.Types.slots(), fn
               item when is_atom(item) -> true
               item when not is_atom(item) -> false
             end)
    end

    test "Guard recognizes all valid values." do
      assert Enum.all?(Roll35Core.Types.slots(), fn
               item when Roll35Core.Types.is_slot(item) -> true
               item when not Roll35Core.Types.is_slot(item) -> false
             end)
    end

    test "Guard rejects invalid values." do
      refute Enum.any?([nil, "", false], fn
               item when Roll35Core.Types.is_slot(item) -> true
               item when not Roll35Core.Types.is_slot(item) -> false
             end)
    end
  end
end
