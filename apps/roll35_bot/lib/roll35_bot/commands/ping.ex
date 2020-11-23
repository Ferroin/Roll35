defmodule Roll35Bot.Commands.Ping do
  @moduledoc """
  Command to check if bot is alive.
  """

  use Roll35Bot.Command
  use Alchemy.Cogs

  Cogs.def ping do
    Roll35Bot.Command.run_cmd(__MODULE__, nil, message, &Cogs.say/1)
  end

  @impl Roll35Bot.Command
  def cmd(_, _), do: {:ok, "pong"}

  @impl Roll35Bot.Command
  def short_desc, do: "Check if the bot is alive."

  @impl Roll35Bot.Command
  def extra_help do
    "Responds with the exact message ‘pong’ if the bot is online and able to respond to messages."
  end
end
