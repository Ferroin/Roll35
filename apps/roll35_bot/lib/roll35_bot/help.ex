defmodule Roll35Bot.Help do
  @moduledoc """
  Command to fetch help and usage information.
  """

  use Alchemy.Cogs

  Cogs.def help do
    Cogs.say("""
    General command syntax:

    `/roll35 <command> [options]`

    Available commands:

    * `armor`: Roll a random mundane armor item.
    * `ping`: Respond with ‘pong’ if the bot is alive.
    * `help`: Get help about a specific command.

    For more info on a command, use `/roll35 help <command>`.
    """)
  end

  Cogs.def help(command) do
    case command do
      "help" ->
        Cogs.say("""
        Usage:

        `/roll35 help [<command>]`

        When run with no parameters, print general help regarding the bot and a list of commands.

        When run with the name of a command, print out more specific help for that command.
        """)

      "ping" ->
        Cogs.say(Roll35Bot.Ping.help())

      "armor" ->
        Cogs.say(Roll35Bot.Armor.help())

      _ ->
        Cogs.say("""
        Error: ‘#{command}’ is not a recognized command.

        Run `/roll35 help` to see a list of known commands.
        """)
    end
  end
end
