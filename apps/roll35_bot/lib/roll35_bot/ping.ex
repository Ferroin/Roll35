defmodule Roll35Bot.Ping do
  @moduledoc """
  Command to check if bot is alive.
  """

  use Alchemy.Cogs

  Cogs.def ping do
    Cogs.say("pong")
  end
end
