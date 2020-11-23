defmodule Roll35Bot.Commands.PingTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.Ping

  test "Command returns correctly." do
    assert {:ok, msg} = Ping.cmd(nil, nil)

    assert String.valid?(msg)
  end

  test "Short description is a valid string." do
    assert String.valid?(Ping.short_desc())
  end

  test "Help text is a valid string." do
    assert String.valid?(Ping.help())
  end
end
