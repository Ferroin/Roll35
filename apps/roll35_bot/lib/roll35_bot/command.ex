defmodule Roll35Bot.Command do
  @moduledoc """
  A basic behaviour to simplify writing commands.
  """

  require Logger

  defmacro __using__(_) do
    name =
      __CALLER__.module
      |> Atom.to_string()
      |> String.split(".")
      |> Enum.at(-1)
      |> String.downcase()

    quote do
      @behaviour Roll35Bot.Command

      @spec help :: String.t()
      def help do
        name = apply(__MODULE__, :name, [])

        {cmdstring, optionstring} =
          if Enum.empty?(options()) do
            {"/roll35 #{name}", ""}
          else
            Enum.reduce(
              options(),
              {"/roll35 #{name}", "\nOptions:\n\n"},
              fn {name, _, _, desc}, {cmdstring, optionstring} ->
                {
                  "#{cmdstring} [--#{Atom.to_string(name)} <#{Atom.to_string(name)}>]",
                  "#{optionstring}**--#{Atom.to_string(name)}**: #{desc}\n"
                }
              end
            )
          end

        """
        #{short_desc()}
        \nUsage:
        \n`#{cmdstring} #{param_names()}`
        #{optionstring}\n#{extra_help()}
        """
      end

      @impl Roll35Bot.Command
      def name, do: unquote(name)

      @impl Roll35Bot.Command
      def options, do: []

      @impl Roll35Bot.Command
      def param_names, do: ""

      defoverridable Roll35Bot.Command
    end
  end

  @typedoc """
  An option for a command.

  The first atom specifies the option name, the second specifies the
  option type, the function returns a list of valid values for the
  option or an empty list if the option is free-form, and the string is
  a short description of the option for the help text.
  """
  @type option :: {atom(), atom(), (term() -> [String.t()]) | (() -> [String.t()]), String.t()}

  @doc """
  Generate the options for the command for parsing.
  """
  @spec get_opt_data(module()) :: OptionParser.options()
  def get_opt_data(module) do
    if Kernel.function_exported?(module, :options, 0) do
      [strict: Enum.map(apply(module, :options, []), fn {name, type, _, _} -> {name, type} end)]
    else
      [strict: []]
    end
  end

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
  @spec run_cmd(module, term(), %Alchemy.Message{}, term()) :: nil
  def run_cmd(module, options, message, reply) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    name = apply(module, :name, [])

    argspec = get_opt_data(module)

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
  Provides the command name.

  A default implementation is provided which returns a lower-case version
  of the last component of the module name.
  """
  @callback name :: String.t()

  @doc """
  Return the short description of this command.

  This is used to assemble the list of known commands for the `help`
  command. The returned value should be a single line.
  """
  @callback short_desc :: String.t()

  @doc """
  Provides extra info for the help text for this command.
  """
  @callback extra_help :: String.t()

  @doc """
  Return a list of options for this command.

  This is parsed to generate both the help text for a command and the
  option list for parsing options for the command. It’s also used to
  simplify testing.

  If not defined, the command will not accept any optional arguments.
  """
  @callback options :: [option()]

  @doc """
  Returns the string to use as a placeholder for paramters in the help text.

  If the command does not accept positional parameters, you do not need
  to implement this callback.
  """
  @callback param_names :: String.t()

  @doc """
  Called to produce random strings of valid positional parameters for the command.

  This is used to generate the help text for a command and to simplify
  testing.

  If the command does not accept positional parameters, you do not need
  to define this callback.
  """
  @callback sample_params :: String.t()

  @optional_callbacks options: 0,
                      sample_params: 0,
                      param_names: 0
end
