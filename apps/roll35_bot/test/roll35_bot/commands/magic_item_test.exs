defmodule Roll35Bot.Commands.MagicItemTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.MagicItem

  test "Short description is a valid string." do
    assert String.valid?(MagicItem.short_desc())
  end

  test "MagicItem text is a valid string." do
    assert String.valid?(MagicItem.help())
  end
end
