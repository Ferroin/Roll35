defmodule Roll35Bot.Ping do
  @moduledoc """
  Command to check if bot is alive.
  """

  use Alchemy.Cogs

  require Logger

  Cogs.def ping do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info("Recieved ping command from #{user}##{tag}.")

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
