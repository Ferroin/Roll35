defmodule Roll35Bot.Commands.WeaponTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.Weapon

  test "Short description is a valid string." do
    assert String.valid?(Weapon.short_desc())
  end

  test "Weapon text is a valid string." do
    assert String.valid?(Weapon.help())
  end
end
