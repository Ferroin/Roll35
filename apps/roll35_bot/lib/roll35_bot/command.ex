defmodule Roll35Bot.Command do
  @moduledoc """
  A basic behaviour to simplify writing commands.
  """

  require Logger

  @doc """
  Parse a command argument string.
  """
  @spec parse(String.t() | nil, OptionParser.options()) ::
          {:ok, {[{atom(), String.t()}] | nil, [String.t()] | nil}} | {:error, String.t()}
  def parse(opts, argspec) when is_binary(opts) do
    {options, args} =
      opts
      |> OptionParser.split()
      |> OptionParser.parse!(argspec)

    {:ok, {args, options}}
  rescue
    e -> {:error, "Unable to parse options: #{Exception.message(e)}"}
  end

  def parse(nil, _) do
    {:ok, {nil, nil}}
  end

  @doc """
  Contains all the boilerplate code for defining the command.
  """
  @spec run_cmd(String.t(), term(), OptionParser.options(), %Alchemy.Message{}, module(), term()) ::
          nil
  def run_cmd(name, options, argspec, message, module, reply) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info(
      "Recieved #{name} command with parameters #{inspect(options)} from #{user}##{tag}."
    )

    try do
      case parse(options, argspec) do
        {:ok, {args, options}} ->
          case apply(module, :cmd, [args, options]) do
            {:ok, msg} ->
              reply.(msg)

            {:error, msg} ->
              reply.("ERROR: #{msg}")

            result ->
              reply.("ERROR: An unknown error occurred, check the bot logs for more info.")
              Logger.error("Recieved unknown return value in #{name} command: #{inspect(result)}")
          end

        {:error, msg} ->
          reply.("ERROR: #{msg}")
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

  The first argument is any positional parameters passed to the command,
  while the second is a keyword list of options passed (based on the
  `argspec` argument passed to `Roll35Bot.Command.run_cmd/6`).
  """
  @callback cmd(list(String.t()), keyword()) :: {:ok | :error, String.t()}

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
