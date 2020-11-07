defmodule Roll35Bot.Ping do
  @moduledoc """
  Command to check if bot is alive.
  """

  use Alchemy.Cogs

  Cogs.def ping do
    Cogs.say("pong")
  end

  @doc """
  Return the help text for this command.
  """
  @spec help :: String.t()
  def help do
    """
    Usage:

    `/roll35 ping`

    Responds with the exact message ‘pong’ if the bot is online and able to respond to messages.
    """
  end
end
