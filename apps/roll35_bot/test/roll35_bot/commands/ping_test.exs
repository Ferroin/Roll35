defmodule Roll35Bot.Commands.PingTest do
  use Roll35Bot.TestHarness, async: true

  alias Roll35Bot.Commands.Ping

  test "Short description is a valid string." do
    assert String.valid?(Ping.short_desc())
  end

  test "Extra help text is a valid string." do
    assert String.valid?(Ping.extra_help())
  end

  test "Command returns correctly." do
    Roll35Bot.TestHarness.valid_command(Ping)
  end
end
