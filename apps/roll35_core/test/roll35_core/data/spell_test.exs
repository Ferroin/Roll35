defmodule Roll35Core.Data.SpellTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Spell

  alias Roll35Core.TestHarness

  @moduletag :tmp_dir

  @spelldata Path.join("priv", "spells.yaml")
  @classdata Path.join("priv", "classes.yaml")

  @class_types ["arcane", "divine", "occult"]
  @safe_name_regex ~r/^[[:lower:]][[:lower:]_]*$/
  @spell_name_regex ~r/(.*) \(.*\)/

  setup context do
    db_path = context.tmp_dir

    {:ok, server} =
      start_supervised(
        {Spell, [name: nil, spellpath: @spelldata, classpath: @classdata, dbpath: db_path]}
      )

    Spell.ready?(server)

    Map.put(context, :server, server)
  end

  describe "Roll35Core.Data.Spell.get_classes/1" do
    test "Returns a list of atoms that fit character limits.", context do
      classes = Spell.get_classes(context.server)

      assert Enum.all?(classes, &is_atom/1)

      Enum.each(classes, fn item ->
        assert is_atom(item)

        assert Regex.match?(@safe_name_regex, Atom.to_string(item))
      end)
    end
  end

  describe "Roll35Core.Data.Spell.get_class/2" do
    test "Properly fetches data for each class.", context do
      classes = Spell.get_classes(context.server)

      Enum.each(classes, fn item ->
        assert {:ok, cls} = Spell.get_class(context.server, item)

        assert is_map(cls)

        assert Map.has_key?(cls, :type)
        assert cls.type in @class_types

        assert Map.has_key?(cls, :levels)
        assert is_list(cls.levels)
        assert Enum.all?(cls.levels, fn i -> i == nil or (is_integer(i) and i > 0) end)

        if Map.has_key?(cls, :copy) do
          refute Map.has_key?(cls, :merge)

          assert is_atom(cls.copy)

          assert {:ok, _} = Spell.get_class(context.server, cls.copy)
        end

        if Map.has_key?(cls, :merge) do
          refute Map.has_key?(cls, :copy)

          assert is_list(cls.merge)

          assert length(cls.merge) > 1

          Enum.each(cls.merge, fn mcls ->
            assert is_atom(mcls)

            assert {:ok, _} = Spell.get_class(context.server, mcls)
          end)
        end
      end)
    end
  end

  describe "Roll35Core.Data.Spell.get_tags/1" do
    test "Returns a valid list of tags.", context do
      tags = Spell.get_tags(context.server)

      Enum.each(tags, fn item ->
        assert String.valid?(item)

        assert Regex.match?(@safe_name_regex, item)
      end)
    end
  end

  describe "Roll35Core.Data.Spell.random/2" do
    test "Properly returns spells.", context do
      Enum.each(TestHarness.iter_slow(), fn _ ->
        {:ok, spell} = Spell.random(context.server)

        assert String.valid?(spell)

        assert [_, name] = Regex.run(@spell_name_regex, spell)

        valid =
          try do
            {:ok, _} = Spell.get_spell(context.server, name)
            true
          rescue
            _ -> false
          end

        assert valid, "Spell '#{name}' is not a valid spell."
      end)
    end

    test "Returns matching spells for a given level.", context do
      Enum.each(TestHarness.iter_slow(), fn _ ->
        level = Enum.random(0..9)

        {:ok, spell} = Spell.random(context.server, level: level)

        assert String.valid?(spell)

        assert [_, name] = Regex.run(@spell_name_regex, spell)

        {valid, info} =
          try do
            {:ok, info} = Spell.get_spell(context.server, name)
            {true, info}
          rescue
            _ -> {false, nil}
          end

        assert valid, "Spell '#{name}' is not a valid spell."

        assert info.minimum == level
      end)
    end

    test "Returns matching spells for a given class.", context do
      classes = Spell.get_classes(context.server)

      Enum.each(TestHarness.iter_slow(), fn _ ->
        class = Enum.random(classes)

        {:ok, spell} = Spell.random(context.server, class: class)

        assert String.valid?(spell)

        assert [_, name] = Regex.run(@spell_name_regex, spell)

        {valid, info} =
          try do
            {:ok, info} = Spell.get_spell(context.server, name)
            {true, info}
          rescue
            _ -> {false, nil}
          end

        assert valid, "Spell '#{name}' is not a valid spell."

        assert class in Map.keys(info)
      end)
    end

    test "Returns matching spells for a given tag.", context do
      tags = Spell.get_tags(context.server)

      Enum.each(TestHarness.iter_slow(), fn _ ->
        tag = Enum.random(tags)

        {:ok, spell} = Spell.random(context.server, tag: tag)

        assert String.valid?(spell)

        assert [_, name] = Regex.run(@spell_name_regex, spell)

        {valid, info} =
          try do
            {:ok, info} = Spell.get_spell(context.server, name)
            {true, info}
          rescue
            _ -> {false, nil}
          end

        assert valid, "Spell '#{name}' is not a valid spell."

        assert tag in info.tags
      end)
    end
  end
end
