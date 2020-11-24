defmodule Roll35Bot.Commands.WeaponTest do
  use Roll35Bot.TestHarness, async: true

  alias Roll35Bot.Commands.Weapon

  test "Short description is a valid string." do
    assert String.valid?(Weapon.short_desc())
  end

  test "Extra help text is a valid string." do
    assert String.valid?(Weapon.extra_help())
  end

  test "Parameter names are a valid string." do
    assert String.valid?(Weapon.param_names())
  end

  test "Works correctly for valid parameters." do
    Roll35Bot.TestHarness.valid_parameters(Weapon)
  end

  test "Correctly returns an error for invalid parameters." do
    Roll35Bot.TestHarness.invalid_parameters(Weapon, ["shield"])
  end
end
