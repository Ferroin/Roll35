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
    * `weapon`: Roll a random mundane weapon.
    * `spell`: Roll a random spell.
    * `magicitem`: Roll a random magic item.
    * `ping`: Respond with ‘pong’ if the bot is alive.
    * `help`: Get help about a specific command.

    For more info on a command, use `/roll35 help <command>`.
    """)
  end

  Cogs.def help(command) do
    cmdinfo = Cogs.all_commands()

    if command in Map.keys(cmdinfo) do
      Cogs.say(cmdhelp(cmdinfo[command]))
    else
      Cogs.say("""
      Error: ‘#{command}’ is not a recognized command.

      Run `/roll35 help` to see a list of known commands.
      """)
    end
  end

  @doc """
  Return help text for this command.
  """
  @spec help :: String.t()
  def help do
    """
    Usage:

    `/roll35 help [<command>]`

    When run with no parameters, print general help regarding the bot and a list of commands.

    When run with the name of a command, print out more specific help for that command.
    """
  end

  @doc false
  defp cmdhelp({module, _, _}) do
    apply(module, :help, [])
  end

  @doc false
  defp cmdhelp({module, _, _, _}) do
    apply(module, :help, [])
  end
end
