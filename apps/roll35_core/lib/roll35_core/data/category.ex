defmodule Roll35Core.Data.Category do
  @moduledoc """
  Data handling for item categories.
  """

  use Roll35Core.Data.Agent, {:category, "priv/category.yaml"}

  alias Roll35Core.Types
  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    data
    |> Util.atomize_map()
    |> Enum.map(fn {key, value} ->
      {key,
       Enum.map(value, fn entry ->
         entry
         |> Util.atomize_map()
         |> Map.update!(:value, &Types.category_from_string/1)
       end)}
    end)
    |> Map.new()
  end

  # This is not actually a compound itemlist, but the data format is
  # identical, so we just use the same selectors.
  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_compound
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_compound
end
