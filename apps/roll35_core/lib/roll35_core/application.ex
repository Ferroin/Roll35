defmodule Roll35Core.Application do
  @moduledoc false

  use Application

  require Logger

  defp name(atom) do
    {:via, Registry, {Roll35Core.Registry, atom}}
  end

  @impl Application
  def start(_type, _args) do
    dbpath = Path.join(Application.fetch_env!(:roll35_core, :data_path), "db")

    File.mkdir_p!(dbpath)

    children = [
      # Registry
      {Registry, keys: :unique, name: Roll35Core.Registry},

      # Unique data agents
      {Roll35Core.Data.Spell,
       [
         name: name(:spell),
         spellpath: Path.join("priv", "spells.yaml"),
         classpath: Path.join("priv", "classes.yaml"),
         dbpath: dbpath
       ]},
      {Roll35Core.Data.Armor,
       [
         name: name(:armor),
         datapath: Path.join("priv", "armor.yaml")
       ]},
      {Roll35Core.Data.Weapon,
       [
         name: name(:weapon),
         datapath: Path.join("priv", "weapon.yaml")
       ]},
      {Roll35Core.Data.Category,
       [
         name: name(:category),
         datapath: Path.join("priv", "category.yaml")
       ]},
      {Roll35Core.Data.Keys,
       [
         name: name(:keys),
         datapath: Path.join("priv", "keys.yaml")
       ]},
      {Roll35Core.Data.Wondrous,
       [
         name: name(:wondrous),
         datapath: Path.join("priv", "wondrous.yaml")
       ]},

      # Compound data agents
      Supervisor.child_spec(
        {Roll35Core.Data.CompoundAgent,
         [
           name: name(:potion),
           datapath: Path.join("priv", "potion.yaml")
         ]},
        id: :potion
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.CompoundAgent,
         [
           name: name(:scroll),
           datapath: Path.join("priv", "scroll.yaml")
         ]},
        id: :scroll
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.CompoundAgent,
         [
           name: name(:wand),
           datapath: Path.join("priv", "wand.yaml")
         ]},
        id: :wand
      ),

      # Ranked data agents
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:belt),
           datapath: Path.join("priv", "belt.yaml")
         ]},
        id: :belt
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:body),
           datapath: Path.join("priv", "body.yaml")
         ]},
        id: :body
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:chest),
           datapath: Path.join("priv", "chest.yaml")
         ]},
        id: :chest
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:eyes),
           datapath: Path.join("priv", "eyes.yaml")
         ]},
        id: :eyes
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:feet),
           datapath: Path.join("priv", "feet.yaml")
         ]},
        id: :feet
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:hand),
           datapath: Path.join("priv", "hand.yaml")
         ]},
        id: :hand
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:head),
           datapath: Path.join("priv", "head.yaml")
         ]},
        id: :head
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:headband),
           datapath: Path.join("priv", "headband.yaml")
         ]},
        id: :headband
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:neck),
           datapath: Path.join("priv", "neck.yaml")
         ]},
        id: :neck
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:ring),
           datapath: Path.join("priv", "ring.yaml")
         ]},
        id: :ring
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:rod),
           datapath: Path.join("priv", "rod.yaml")
         ]},
        id: :rod
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:shoulders),
           datapath: Path.join("priv", "shoulders.yaml")
         ]},
        id: :shoulders
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:slotless),
           datapath: Path.join("priv", "slotless.yaml")
         ]},
        id: :slotless
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:staff),
           datapath: Path.join("priv", "staff.yaml")
         ]},
        id: :staff
      ),
      Supervisor.child_spec(
        {Roll35Core.Data.RankedAgent,
         [
           name: name(:wrists),
           datapath: Path.join("priv", "wrists.yaml")
         ]},
        id: :wrists
      )
    ]

    opts = [strategy: :one_for_one, name: Roll35Core.Supervisor]
    result = Supervisor.start_link(children, opts)

    Logger.notice("Roll35 Core started.")

    result
  end
end
