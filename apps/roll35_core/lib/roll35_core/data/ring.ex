defmodule Roll35Core.Data.Ring do
  @moduledoc """
  Data handling for rings.
  """

  use Roll35Core.Data.Agent, {:ring, "priv/ring.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_ranked
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_ranked
  defdelegate random(agent, rank, subrank), to: Roll35Core.Data.Agent, as: :random_ranked
end
