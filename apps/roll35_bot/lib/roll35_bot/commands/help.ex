defmodule Roll35Bot.Commands.Help do
  @moduledoc """
  Command to fetch help and usage information.
  """

  use Alchemy.Cogs

  require Logger

  Cogs.def help do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    cmdinfo = Cogs.all_commands()

    Logger.info("Recieved help command from #{user}##{tag}.")

    """
    General command syntax:

    `/roll35 <command> [options]`

    Available commands:

    <%= Enum.each(cmdinfo, fn name, info -> %>
    * `<%= name %>`: <%= cmddesc(info) %>
    <% end) %>

    For more info on a command, use `/roll35 help <command>`.

    Note that invalid commands will be ignored instead of returning an error.
    """
    |> EEx.eval_string()
    |> Cogs.say()
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

  defp cmdhelp({module, _, _}), do: apply(module, :help, [])
  defp cmdhelp({module, _, _, _}), do: apply(module, :help, [])

  defp cmddesc({module, _, _}), do: apply(module, :short_desc, [])
  defp cmddesc({module, _, _, _}), do: apply(module, :short_desc, [])
end
