Logger.configure(level: :warn)

Application.load(:roll35_core)

{:ok, _} = Application.ensure_all_started(:roll35_core)

:ready = Roll35Core.Data.Spell.ready?({:via, Registry, {Roll35Core.Registry, :spell}})

ExUnit.start(capture_log: true)

defmodule Roll35Bot.TestHarness do
  use ExUnit.CaseTemplate

  defp random_options(opts, required, extra) do
    count = Enum.random(1..length(opts))

    required_opts =
      Enum.map(required, fn name ->
        {_, _, fun, _} = opts[name]

        {name, fun}
      end)

    opts
    |> Enum.shuffle()
    |> Enum.take(count)
    |> Enum.map(fn {name, _, fun, _} -> {name, fun} end)
    |> Keyword.merge(required_opts)
    |> Enum.reduce([], fn {name, fun}, acc ->
      arity = :erlang.fun_info(fun)[:arity]

      key =
        if Keyword.has_key?(extra, name) do
          extra[name]
        else
          nil
        end

      cond do
        arity == 0 ->
          [{name, Enum.random(fun.())} | acc]

        arity == 1 ->
          [{name, Enum.random(fun.(key))} | acc]

        true ->
          flunk("Invalid test function for option #{name}, must be a function of 0 or 1 arity.")
      end
    end)
  end

  @spec iter :: pos_integer()
  def iter, do: 1..10_000

  @spec iter_slow :: pos_integer()
  def iter_slow, do: 1..200

  @spec valid_command(module()) :: nil
  def valid_command(module) do
    assert {:ok, msg} = apply(module, :cmd, [[], []])

    assert String.valid?(msg)
  end

  @spec valid_parameters(module()) :: nil
  def valid_parameters(module) do
    Enum.each(iter_slow(), fn _ ->
      param = apply(module, :sample_params, [])

      assert {:ok, msg} = apply(module, :cmd, [[param], []])

      assert String.valid?(msg)
    end)
  end

  @spec invalid_parameters(module(), String.t()) :: nil
  def invalid_parameters(module, params) do
    assert {:error, msg} = apply(module, :cmd, [params, []])

    assert String.valid?(msg)
  end

  @spec valid_option(module(), atom()) :: nil
  def valid_option(module, option) do
    opts = apply(module, :options, [])

    valid_opts =
      Enum.reduce_while(opts, nil, fn {name, _, fun, _}, _ ->
        if name == option do
          {:halt, fun.()}
        else
          {:cont, nil}
        end
      end)

    if valid_opts == nil do
      flunk("Option #{option} not found in module #{module}.")
    end

    Enum.each(iter_slow(), fn _ ->
      value = Enum.random(valid_opts)

      assert {:ok, msg} = apply(module, :cmd, [[], [{option, value}]])

      assert String.valid?(msg)
    end)
  end

  @spec invalid_option(module(), atom(), String.t()) :: nil
  def invalid_option(module, option, value) do
    assert {:error, msg} = apply(module, :cmd, [[], [{option, value}]])

    assert String.valid?(msg)
  end

  @spec permute_options(module(), [[atom()]], Regex.t(), keyword()) :: nil
  def permute_options(module, required, errors \\ ~r/a^/, extra \\ []) do
    opts = apply(module, :options, [])

    Enum.each(iter_slow(), fn _ ->
      options = random_options(opts, required, extra)

      assert {ret, msg} = apply(module, :cmd, [[], options])

      case ret do
        :ok ->
          assert String.valid?(msg)

        :error ->
          assert String.valid?(msg), "Invalid error message for options #{inspect(options)}"

          assert Regex.match?(errors, msg),
                 "Invalid error message \"#{inspect(msg)}\" for options #{inspect(options)}"

        _ ->
          flunk("Recieved invalid return value #{inspect({ret, msg})}.")
      end
    end)
  end
end
