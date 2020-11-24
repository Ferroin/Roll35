defmodule Roll35Bot.Commands.HelpTest do
  use ExUnit.Case, async: true

  alias Roll35Bot.Commands.Help

  test "Short description is a valid string." do
    assert String.valid?(Help.short_desc())
  end

  test "Extra help is a valid string." do
    assert String.valid?(Help.extra_help())
  end

  test "Paramter names are a valid string." do
    assert String.valid?(Help.param_names())
  end
end
