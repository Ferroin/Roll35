defmodule Roll35Bot.Commands.SpellTest do
  use Roll35Bot.TestHarness, async: true

  alias Roll35Bot.Commands.Spell

  test "Short description is a valid string." do
    assert String.valid?(Spell.short_desc())
  end

  test "Extra help text is a valid string." do
    assert String.valid?(Spell.extra_help())
  end

  test "Returns correctly when invoked without options." do
    Roll35Bot.TestHarness.valid_command(Spell)
  end

  test "Returns a valid message when invoked with level option." do
    Roll35Bot.TestHarness.valid_option(Spell, :level)
  end

  test "Returns a valid message when invoked with class option." do
    Roll35Bot.TestHarness.valid_option(Spell, :class)
  end

  test "Returns a valid message when invoked with tag option." do
    Roll35Bot.TestHarness.valid_option(Spell, :tag)
  end

  test "Returns a valid message when invoked with randomized options." do
    Roll35Bot.TestHarness.permute_options(
      Spell,
      [],
      ~r/No spells found for the requested parameters./,
      []
    )
  end

  test "Returns an error for invalid options." do
    Roll35Bot.TestHarness.invalid_option(Spell, :level, -1)
    Roll35Bot.TestHarness.invalid_option(Spell, :class, "fighter")
    Roll35Bot.TestHarness.invalid_option(Spell, :tag, "kleptomania")
  end
end
