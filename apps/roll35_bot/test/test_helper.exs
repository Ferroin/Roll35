Logger.configure(level: :warn)

Application.load(:roll35_core)

{:ok, _} = Application.ensure_all_started(:roll35_core)

:ready = Roll35Core.Data.Spell.ready?({:via, Registry, {Roll35Core.Registry, :spell}})

ExUnit.start(capture_log: true)

defmodule Roll35Bot.TestHarness do
  @moduledoc false

  @spec iter :: pos_integer()
  def iter, do: 1..10_000

  @spec iter_slow :: pos_integer()
  def iter_slow, do: 1..200
end
