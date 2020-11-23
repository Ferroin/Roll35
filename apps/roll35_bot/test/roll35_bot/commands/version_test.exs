defmodule Roll35Bot.Commands.VersionTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.Version

  test "Command returns correctly." do
    assert {:ok, msg} = Version.cmd(nil, nil)

    assert String.valid?(msg)
  end

  test "Short description is a valid string." do
    assert String.valid?(Version.short_desc())
  end

  test "Help text is a valid string." do
    assert String.valid?(Version.help())
  end
end
