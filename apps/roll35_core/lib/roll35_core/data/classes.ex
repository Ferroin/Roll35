defmodule Roll35Core.Data.Classes do
  @moduledoc """
  Data handling for classes.
  """

  use Roll35Core.Data.Agent, "priv/classes.yaml"

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    _ = [:arcane, :divine, :occult]

    data
    |> Util.atomize_map()
    |> Enum.map(fn {key, value} ->
      {
        key,
        value
        |> (fn item ->
              Map.update!(item, :type, &String.to_existing_atom/1)
            end).()
        |> (fn item ->
              if Map.has_key?(item, :copy) do
                Map.update!(item, :copy, &String.to_existing_atom/1)
              else
                item
              end
            end).()
        |> (fn item ->
              if Map.has_key?(item, :merge) do
                Map.update!(item, :merge, fn value ->
                  Enum.map(value, &String.to_existing_atom/1)
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
