defmodule Roll35Bot.Application do
  @moduledoc false

  use Application

  alias Alchemy.Client
  alias Alchemy.Cogs

  require Logger

  @impl Application
  def start(_type, _args) do
    {:ok, _} = Application.ensure_all_started(:roll35_core, :permanent)
    run = Client.start(System.fetch_env!("DISCORD_TOKEN"))

    Cogs.set_prefix("/roll35 ")

    use Roll35Bot.Commands.Help
    use Roll35Bot.Commands.Ping
    use Roll35Bot.Commands.Version
    use Roll35Bot.Commands.Armor
    use Roll35Bot.Commands.Weapon
    use Roll35Bot.Commands.Spell
    use Roll35Bot.Commands.MagicItem

    Logger.notice("Roll35 Bot started.")

    run
  end
end
