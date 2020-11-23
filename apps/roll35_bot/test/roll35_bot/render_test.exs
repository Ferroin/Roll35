defmodule Roll35Bot.RendererTest do
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Keys
  alias Roll35Core.Data.Spell

  alias Roll35Bot.Renderer

  alias Roll35Bot.TestHarness

  @keys_server {:via, Registry, {Roll35Core.Registry, :keys}}
  @spell_server {:via, Registry, {Roll35Core.Registry, :spell}}

  describe "Roll35Bot.Renderer.render/1" do
    test "Properly passes plain UTF-8 strings unmodified." do
      Enum.each(
        [
          "",
          "Simple ASCII String.",
          "Här är några utökade latinska tecken.",
          "Και μερικά ελληνικά.",
          "Далее идет кириллица.",
          "بعض اللغة العربية لقياس جيد",
          "そして最後に日本人。"
        ],
        fn i ->
          assert {:ok, i} == Renderer.render(i)
        end
      )
    end

    test "Properly formats EEx template code." do
      Enum.each(
        [
          {"Simple <%= \"ASCII\" %> String.", "Simple ASCII String."},
          {"Här är <%= \"några\" %> utökade latinska tecken.",
           "Här är några utökade latinska tecken."},
          {"Και <%= \"μερικά\" %> ελληνικά.", "Και μερικά ελληνικά."},
          {"Далее <%= \"идет\" %> кириллица.", "Далее идет кириллица."},
          {"بعض اللغة <%= \"العربية\" %> لقياس جيد", "بعض اللغة العربية لقياس جيد"},
          {"<%= \"そして\" %>最後に日本人。", "そして最後に日本人。"}
        ],
        fn {t, f} ->
          assert {:ok, f} == Renderer.render(t)
        end
      )
    end

    test "Fetches key data from Roll35Core properly." do
      Enum.each([:flat, :flat_proportional, :grouped, :grouped_proportional], fn t ->
        Enum.each(Keys.get_keys(@keys_server, t), fn k ->
          if t in [:grouped, :grouped_proportional] do
            {:ok, subkeys} = Keys.get_subkeys(@keys_server, k)

            Enum.each(subkeys, fn s ->
              assert {:ok, item} =
                       Renderer.render("<%= key.(key: #{inspect(k)}, subkey: #{inspect(s)}) %>")

              assert String.valid?(item)
              assert String.length(item) > 0
            end)
          else
            assert {:ok, item} = Renderer.render("<%= key.(key: #{inspect(k)}) %>")

            assert String.valid?(item)
            assert String.length(item) > 0
          end
        end)
      end)
    end
  end

  describe "Roll35Bot.Renderer.render/2" do
    test "Properly handles putting spells into templates." do
      classes = [
        :minimum,
        :spellpage,
        :spellpage_arcane,
        :spellpage_divine,
        :random | Spell.get_classes(@spell_server)
      ]

      Enum.each(TestHarness.iter_slow(), fn _ ->
        class = Enum.random(classes)

        assert {:ok, item} = Renderer.render("<%= spell %>", %{cls: class})

        assert String.valid?(item)
        assert String.length(item)
      end)
    end

    test "Returns error status for bogus spell info." do
      assert {:error, msg} = Renderer.render("<%= spell %>", %{cls: :invalid})

      assert String.valid?(msg)
      assert String.length(msg)
    end
  end

  describe "Roll35Bot.Renderer.format/1" do
    test "Passes strings through unmodified." do
      Enum.each(
        [
          "",
          "Simple ASCII String.",
          "Här är några utökade latinska tecken.",
          "Και μερικά ελληνικά.",
          "Далее идет кириллица.",
          "بعض اللغة العربية لقياس جيد",
          "そして最後に日本人。"
        ],
        fn i ->
          assert i == Renderer.format(i)
        end
      )
    end

    test "Handles items without spell key by passing to render/1" do
      Enum.each(
        [
          {"Simple <%= \"ASCII\" %> String.", "Simple ASCII String."},
          {"Här är <%= \"några\" %> utökade latinska tecken.",
           "Här är några utökade latinska tecken."},
          {"Και <%= \"μερικά\" %> ελληνικά.", "Και μερικά ελληνικά."},
          {"Далее <%= \"идет\" %> кириллица.", "Далее идет кириллица."},
          {"بعض اللغة <%= \"العربية\" %> لقياس جيد", "بعض اللغة العربية لقياس جيد"},
          {"<%= \"そして\" %>最後に日本人。", "そして最後に日本人。"}
        ],
        fn {t, f} ->
          assert f == Renderer.format(%{name: t})
        end
      )
    end

    test "Handles items with spell key by passing to render/2" do
      classes = [
        :minimum,
        :spellpage,
        :spellpage_arcane,
        :spellpage_divine,
        :random | Spell.get_classes(@spell_server)
      ]

      Enum.each(TestHarness.iter_slow(), fn _ ->
        class = Enum.random(classes)

        item = Renderer.format(%{name: "<%= spell %>", spell: %{cls: class}})

        assert String.valid?(item)
        assert String.length(item)
      end)
    end

    test "Returns error messages correctly." do
      msg = Renderer.format(%{name: "<%= spell %>", spell: %{cls: :invalid}})

      assert String.valid?(msg)
      assert String.length(msg)
    end
  end
end
