defmodule Roll35Bot.Command do
  @moduledoc """
  A basic behaviour to simplify writing commands.
  """

  require Logger

  @doc """
  Contains all the boilerplate code for defining the command.
  """
  @spec run_cmd(String.t(), term(), %Alchemy.Message{}, module(), term()) :: nil
  def run_cmd(name, options, message, module, reply) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info("Recieved armor command with parameters #{inspect(options)} from #{user}##{tag}.")

    try do
      case apply(module, :cmd, [options]) do
        {:ok, msg} ->
          reply.(msg)

        {:error, msg} ->
          reply.("ERROR: #{msg}")

        result ->
          reply.("ERROR: An unknown error occurred, check the bot logs for more info.")
          Logger.error("Recieved unknown return value in #{name} command: #{inspect(result)}")
      end
    rescue
      e ->
        reply.("ERROR: An internal error occurred, please check the bot logs for more info.")
        reraise e, __STACKTRACE__
    catch
      :exit, info ->
        reply.("ERROR: An internal error occurred, please check the bot logs for more info.")
        exit(info)
    end
  end

  @doc """
  The callback that actually runs the command.

  This should take an arbitrary term as options (produced by the
  `Roll35Bot.Command.parse_options/1` callback). and return a success or error state with an
  associated message. The returned message is what gets sent to the user.
  """
  @callback cmd(term()) :: {:ok | :error, String.t()}

  @doc """
  Return the help text for this command.

  This will be scraped by the `help` command to provide users with help
  specific to this command.
  """
  @callback help :: String.t()

  @doc """
  Return the short description of this command.

  This is used to assemble the list of known commands for the `help`
  command. The returned value should be a single line.
  """
  @callback short_desc :: String.t()
end
