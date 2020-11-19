defmodule Roll35Core.Data.Potion do
  @moduledoc """
  Data handling for potions.
  """

  use Roll35Core.Data.Agent, "priv/potion.yaml"

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_compound_itemlist(data)
  end

  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_compound
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_compound
end
