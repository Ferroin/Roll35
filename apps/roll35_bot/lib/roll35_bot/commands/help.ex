defmodule Roll35Bot.Commands.Help do
  @moduledoc """
  Command to fetch help and usage information.
  """

  use Roll35Bot.Command
  use Alchemy.Cogs

  require Logger

  defp cmdhelp({module, _, _}), do: module.help()
  defp cmdhelp({module, _, _, _}), do: module.help()

  defp get_cmd_list do
    Cogs.all_commands()
    |> Enum.map(fn
      {name, {mod, _, _}} -> "* `#{name}`: #{mod.short_desc()}"
      {name, {mod, _, _, _}} -> "* `#{name}`: #{mod.short_desc()}"
    end)
    |> Enum.sort()
    |> Enum.join("\n")
  end

  Cogs.def help do
    Roll35Bot.Command.run_cmd(__MODULE__, nil, message, &Cogs.say/1)
  end

  Cogs.def help(command) do
    Roll35Bot.Command.run_cmd(__MODULE__, command, message, &Cogs.say/1)
  end

  @impl Roll35Bot.Command
  def cmd(nil, _) do
    cmdlist = get_cmd_list()

    {:ok,
     """
     General command syntax:

     `/roll35 <command> [options]`

     Available commands:

     #{cmdlist}

     For more info on a command, use `/roll35 help <command>`.

     Note that invalid commands will be ignored instead of returning an error.
     """}
  end

  def cmd([command], _) do
    cmdinfo = Cogs.all_commands()

    if command in Map.keys(cmdinfo) do
      {:ok, cmdhelp(cmdinfo[command])}
    else
      {:error,
       """
       ‘#{command}’ is not a recognized command.

       Run `/roll35 help` to see a list of available commands.
       """}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Get help with using the bot."

  @impl Roll35Bot.Command
  def extra_help do
    """
    When run with no parameters, print general help regarding the bot and a list of commands.

    When run with the name of a command, print out more specific help for that command.
    """
  end

  @impl Roll35Bot.Command
  def param_names, do: "[<command>]"

  @impl Roll35Bot.Command
  def sample_params, do: "help"
end
