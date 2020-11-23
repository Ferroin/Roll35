defmodule Roll35Bot.Commands.ArmorTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.Armor

  test "Short description is a valid string." do
    assert String.valid?(Armor.short_desc())
  end

  test "Armor text is a valid string." do
    assert String.valid?(Armor.help())
  end
end
