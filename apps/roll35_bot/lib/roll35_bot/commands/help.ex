defmodule Roll35Bot.Commands.Help do
  @moduledoc """
  Command to fetch help and usage information.
  """

  use Alchemy.Cogs

  require Logger

  defp cmdhelp({module, _, _}), do: apply(module, :help, [])
  defp cmdhelp({module, _, _, _}), do: apply(module, :help, [])

  defp get_cmd_list do
    Cogs.all_commands()
    |> Enum.map(fn
      {name, {mod, _, _}} -> "* `#{name}`: #{apply(mod, :short_desc, [])}"
      {name, {mod, _, _, _}} -> "* `#{name}`: #{apply(mod, :short_desc, [])}"
    end)
    |> Enum.sort()
    |> Enum.join("\n")
  end

  Cogs.def help do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    cmdlist = get_cmd_list()

    Logger.info("Recieved help command from #{user}##{tag}.")

    Cogs.say("""
    General command syntax:

    `/roll35 <command> [options]`

    Available commands:

    #{cmdlist}

    For more info on a command, use `/roll35 help <command>`.

    Note that invalid commands will be ignored instead of returning an error.
    """)
  end

  Cogs.def help(command) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info("Recieved help #{command} command from #{user}##{tag}.")

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
  Return a short description for this command.
  """
  @spec short_desc :: String.t()
  def short_desc, do: "Get help about a specific command."

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
end
