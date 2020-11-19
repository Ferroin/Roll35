defmodule Roll35Core.Data.Wand do
  @moduledoc """
  Data handling for wands.
  """

  use Roll35Core.Data.Agent, "priv/wand.yaml"

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_compound_itemlist(data)
  end

  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_compound
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_compound
end
