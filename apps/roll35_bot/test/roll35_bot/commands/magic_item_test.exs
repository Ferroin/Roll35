defmodule Roll35Bot.Commands.MagicItemTest do
  use Roll35Bot.TestHarness, async: true

  alias Roll35Bot.Commands.MagicItem

  test "Short description is a valid string." do
    assert String.valid?(MagicItem.short_desc())
  end

  test "Extra help text is a valid string." do
    assert String.valid?(MagicItem.extra_help())
  end

  test "Returns correctly when invoked without options." do
    Roll35Bot.TestHarness.valid_command(MagicItem)
  end

  test "Returns correctly when invoked with rank option." do
    Roll35Bot.TestHarness.valid_option(MagicItem, :rank)
  end

  test "Returns correctly when invoked with type option." do
    Roll35Bot.TestHarness.valid_option(MagicItem, :type)
  end

  test "Returns an error for invalid options." do
    Roll35Bot.TestHarness.invalid_option(MagicItem, :rank, "bogus")
  end
end
