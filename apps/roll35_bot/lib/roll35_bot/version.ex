defmodule Roll35Bot.Version do
  @moduledoc """
  Provide a command to return version information.
  """

  use Alchemy.Cogs

  require Logger

  @app_version Roll35.MixProject.project()[:version]
  @bot_version Roll35Bot.MixProject.project()[:version]
  @core_version Roll35Core.MixProject.project()[:version]
  @build_time DateTime.to_iso8601(DateTime.utc_now())

  Cogs.def version do
    Cogs.say("""
    App Version: #{@app_version}
    Bot Code Version: #{@bot_version}
    Core Code Version: #{@core_version}
    Build Time: #{@build_time}
    """)
  end

  @doc """
  Return help for this command.
  """
  @spec help :: String.t()
  def help do
    """
    Usage:

    `/roll35 version`

    Print out version and build information for the bot.
    """
  end
end
