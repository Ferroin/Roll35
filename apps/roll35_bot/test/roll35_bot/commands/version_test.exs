defmodule Roll35Bot.Commands.VersionTest do
  use Roll35Bot.TestHarness, async: true

  alias Roll35Bot.Commands.Version

  test "Short description is a valid string." do
    assert String.valid?(Version.short_desc())
  end

  test "Extra help text is a valid string." do
    assert String.valid?(Version.extra_help())
  end

  test "Command returns correctly." do
    Roll35Bot.TestHarness.valid_command(Version)
  end
end
