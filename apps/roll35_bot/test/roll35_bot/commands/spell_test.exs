defmodule Roll35Bot.Commands.SpellTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.Spell

  test "Short description is a valid string." do
    assert String.valid?(Spell.short_desc())
  end

  test "Spell text is a valid string." do
    assert String.valid?(Spell.help())
  end
end
