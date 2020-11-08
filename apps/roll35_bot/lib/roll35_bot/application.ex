defmodule Roll35Bot.Application do
  @moduledoc false

  use Application
  alias Alchemy.Client
  alias Alchemy.Cogs

  @impl Application
  def start(_type, _args) do
    {:ok, _} = Application.ensure_all_started(:roll35_core, :permanent)
    run = Client.start(System.fetch_env!("DISCORD_TOKEN"))
    Cogs.set_prefix("/roll35 ")
    use Roll35Bot.Help
    use Roll35Bot.Ping
    use Roll35Bot.Armor
    use Roll35Bot.Weapon
    run
  end
end
