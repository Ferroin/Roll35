defmodule Roll35Bot.Commands.ArmorTest do
  use Roll35Bot.TestHarness, async: true

  alias Roll35Bot.Commands.Armor

  test "Short description is a valid string." do
    assert String.valid?(Armor.short_desc())
  end

  test "Extra help text is a valid string." do
    assert String.valid?(Armor.extra_help())
  end

  test "Parameter names are a valid string." do
    assert String.valid?(Armor.param_names())
  end

  test "Works correctly for valid parameters." do
    Roll35Bot.TestHarness.valid_parameters(Armor)
  end

  test "Correctly returns an error for invalid parameters." do
    Roll35Bot.TestHarness.invalid_parameters(Armor, ["melee"])
  end
end
