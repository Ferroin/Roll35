defmodule Roll35Bot.Commands.Version do
  @moduledoc """
  Provide a command to return version information.
  """

  use Roll35Bot.Command
  use Alchemy.Cogs

  @app_version Roll35.MixProject.project()[:version]
  @bot_version Roll35Bot.MixProject.project()[:version]
  @core_version Roll35Core.MixProject.project()[:version]
  @build_time DateTime.to_iso8601(DateTime.utc_now())

  Cogs.def version do
    Roll35Bot.Command.run_cmd(__MODULE__, nil, message, &Cogs.say/1)
  end

  @impl Roll35Bot.Command
  def cmd(_, _) do
    {
      :ok,
      """
      App Version: #{@app_version}
      Bot Code Version: #{@bot_version}
      Core Code Version: #{@core_version}
      Build Time: #{@build_time}
      """
    }
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Get info about the version of the running bot."

  @impl Roll35Bot.Command
  def extra_help, do: "Print out version and build information for the bot."
end
