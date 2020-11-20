defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  require Logger

  defp name(atom) do
    {:via, Registry, {Roll35Core.Registry, atom}}
  end

  @impl Application
  def start(_type, _args) do
    Enum.each(
      [
        "db"
      ],
      fn item ->
        path = Path.join(Application.fetch_env!(:roll35_core, :data_path), "db")

        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        Application.put_env(:roll35_core, String.to_atom("#{item}_path"), path, persistent: true)

        File.mkdir_p!(path)
      end
    )

    children = [
      # Registry
      {Registry, keys: :unique, name: Roll35Core.Registry},

      # Unique data agents
      {Roll35Core.Data.Spell,
       {name(:spell), Path.join("priv", "spells.yaml"), Path.join("priv", "classes.yaml")}},
      {Roll35Core.Data.Armor, {name(:armor), Path.join("priv", "armor.yaml")}},
      {Roll35Core.Data.Weapon, {name(:weapon), Path.join("priv", "weapon.yaml")}},
      {Roll35Core.Data.Category, {name(:caegory), Path.join("priv", "category.yaml")}},
      {Roll35Core.Data.Keys, {name(:keys), Path.join("priv", "keys.yaml")}},
      {Roll35Core.Data.Wondrous, {name(:wondrous), Path.join("priv", "wondrous.yaml")}},

      # Compound data agents
      Supervisor.child_spec(
        {Roll35Core.Data.CompoundAgent, {name(:potion), Path.join("priv", "potion.yaml")}},
        id: :potion
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.CompoundAgent, {name(:scroll), Path.join("priv", "scroll.yaml")}},
        id: :scroll
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.CompoundAgent, {name(:wand), Path.join("priv", "wand.yaml")}},
        id: :wand
      ),

      # Ranked data agents
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:belt), Path.join("priv", "belt.yaml")}},
        id: :belt
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:body), Path.join("priv", "body.yaml")}},
        id: :body
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:chest), Path.join("priv", "chest.yaml")}},
        id: :chest
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:eyes), Path.join("priv", "eyes.yaml")}},
        id: :eyes
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:feet), Path.join("priv", "feet.yaml")}},
        id: :feet
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:hand), Path.join("priv", "hand.yaml")}},
        id: :hand
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:head), Path.join("priv", "head.yaml")}},
        id: :head
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:headband), Path.join("priv", "headband.yaml")}},
        id: :headband
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:neck), Path.join("priv", "neck.yaml")}},
        id: :neck
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:ring), Path.join("priv", "ring.yaml")}},
        id: :ring
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:rod), Path.join("priv", "rod.yaml")}},
        id: :rod
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:shoulders), Path.join("priv", "shoulders.yaml")}},
        id: :shoulders
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:slotless), Path.join("priv", "slotless.yaml")}},
        id: :slotless
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:staff), Path.join("priv", "staff.yaml")}},
        id: :staff
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent, {name(:wrists), Path.join("priv", "wrists.yaml")}},
        id: :wrists
      )
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    result = Supervisor.start_link(children, opts)

    Logger.notice("Roll35 Core started.")

    result
  end
end
