defmodule Roll35Core.Data.Keys do
  @moduledoc """
  Data handling for template keys.
  """

  use Roll35Core.Data.Agent, "priv/keys.yaml"

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    data
    |> Util.atomize_map()
    |> Enum.map(fn {key, value} ->
      {
        key,
        value
        # credo:disable-for-next-line Credo.Check.Warning.UnsafeToAtom
        |> Map.update!(:type, &String.to_atom/1)
        |> (fn item ->
              if item.type in [:flat_proportional, :grouped_proportional] do
                Map.update!(item, :data, fn data ->
                  data
                  |> Enum.map(fn {key, value} ->
                    {
                      key,
                      Enum.map(value, &Util.atomize_map/1)
                    }
                  end)
                  |> Map.new()
                end)
              else
                item
              end
            end).()
      }
    end)
    |> Map.new()
  end
end
