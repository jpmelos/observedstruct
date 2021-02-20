import operator

import pytest

from observedstruct import (
    ObservedDict,
    ObservedList,
    ObservedOperation,
    get_item_for_reference,
)


def pre_callback(*args):
    pre_callback.call_args.append(args)


def post_callback(*args):
    post_callback.call_args.append(args)


@pytest.fixture(autouse=True)
def _reset_callback():
    pre_callback.call_args = []
    post_callback.call_args = []


def test_get_item_for_reference():
    d = ObservedDict({"a": [1]})
    assert get_item_for_reference(d, ["a", 0]) == 1


class TestObservedDict:
    class TestInstantiation:
        def test_instantiation_without_arguments(self):
            d = ObservedDict()
            assert d == {}

        def test_instantiation_with_empty_dict(self):
            d = ObservedDict({})
            assert d == {}

        def test_instantiation_with_dict(self):
            d = ObservedDict({"a": 1})
            assert d == {"a": 1}
            assert d["a"] == 1

        def test_instantiation_with_another_observed_dict(self):
            d = ObservedDict(ObservedDict({"a": 1}))
            assert d == {"a": 1}
            assert isinstance(d._struct, dict)

        def test_instantiation_with_nested_dict(self):
            d = ObservedDict({"a": {"b": 2}})
            assert d == {"a": {"b": 2}}
            assert d["a"] == {"b": 2}
            assert d["a"]["b"] == 2
            assert isinstance(d["a"], ObservedDict)
            assert d["a"]._parent is d
            assert d["a"]._reference_in_parent == "a"

        def test_instantiation_with_another_observed_struct_type(self):
            d = ObservedDict({"a": [1, 2]})
            assert d == {"a": [1, 2]}
            assert d["a"] == [1, 2]
            assert isinstance(d["a"], ObservedList)
            assert d["a"]._parent is d
            assert d["a"]._reference_in_parent == "a"

    def test_comparison(self):
        d = ObservedDict({"a": {"b": 2}})
        assert d == ObservedDict({"a": {"b": 2}})
        assert d["a"] == ObservedDict({"b": 2})
        assert d == ObservedDict({"a": ObservedDict({"b": 2})})
        assert d == {"a": {"b": 2}}
        assert d["a"] == {"b": 2}

    class TestDictInterface:
        @pytest.fixture
        def d(self):
            return ObservedDict({"a": 1, "b": 2})

        def test_length(self, d):
            assert len(d) == 2
            assert operator.length_hint(d) == 2

        def test_keys_list(self, d):
            assert list(d) == ["a", "b"]

        def test_keys_iter(self, d):
            assert list(iter(d)) == ["a", "b"]

        def test_key_membership(self, d):
            assert "a" in d
            assert "c" not in d

        def test_reversed(self, d):
            assert list(reversed(d)) == ["b", "a"]

        def test_get(self, d):
            assert d.get("a") == d["a"]
            assert d.get("c", "c") == "c"

        def test_items(self, d):
            assert list(d.items()) == [("a", 1), ("b", 2)]
            assert d.keys() == d._struct.keys()

        def test_pop(self, d):
            assert d.pop("b") == 2
            assert "b" not in d
            assert d.pop("b", 3) == 3

        def test_setdefault(self, d):
            assert d.setdefault("b", 3) == 2
            del d["b"]
            assert d.setdefault("b", 3) == 3
            assert d["b"] == 3

        def test_popitem(self, d):
            assert d.popitem() == ("b", 2)
            assert "b" not in d

        def test_popitem_from_empty_dict(self):
            d = ObservedDict()
            with pytest.raises(KeyError):
                d.popitem()

        def test_update(self, d):
            d.update({"c": 3})
            assert d["c"] == 3

        def test_values_list(self, d):
            assert list(d.values()) == [1, 2]

        def test_clear(self, d):
            d.clear()
            assert len(d) == 0

        def test_or_operation(self, d):
            other_d = d | {"c": 3}
            assert d == {"a": 1, "b": 2}
            assert other_d == {"a": 1, "b": 2, "c": 3}

        def test_ior_operation(self, d):
            d |= {"c": 3}
            assert d == {"a": 1, "b": 2, "c": 3}

    class TestScalars:
        def test_add(self):
            d = ObservedDict(
                pre_callbacks=[pre_callback], post_callbacks=[post_callback]
            )
            d["a"] = 1

            assert pre_callback.call_args == [
                (d, ObservedOperation.Add, ["a"], None, 1)
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Add, ["a"], None, 1)
            ]

            assert d == {"a": 1}

        def test_update(self):
            d = ObservedDict(
                {"a": 1},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            d["a"] = 2

            assert pre_callback.call_args == [
                (d, ObservedOperation.Update, ["a"], 1, 2)
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Update, ["a"], 1, 2)
            ]

            assert d == {"a": 2}

        def test_delete(self):
            d = ObservedDict(
                {"a": 1},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            del d["a"]

            assert pre_callback.call_args == [
                (d, ObservedOperation.Remove, ["a"], 1, None)
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Remove, ["a"], 1, None)
            ]

            assert d == {}

        def test_access(self):
            d = ObservedDict(
                {"a": 1},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            assert d["a"] == 1

            assert pre_callback.call_args == [
                (d, ObservedOperation.Access, ["a"], None, None)
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Access, ["a"], None, None)
            ]

            assert d == {"a": 1}

    class TestNested:
        def test_add_scalar_to_nested_struct(self):
            d = ObservedDict(
                {"nested": {}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            d["nested"]["a"] = 1

            assert pre_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Add, ["nested", "a"], None, 1),
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Add, ["nested", "a"], None, 1),
            ]

            assert d == {"nested": {"a": 1}}

        def test_add_nested_struct(self):
            d = ObservedDict(
                pre_callbacks=[pre_callback], post_callbacks=[post_callback]
            )
            d["nested"] = {"a": 1}

            assert pre_callback.call_args == [
                (d, ObservedOperation.Add, ["nested"], None, {"a": 1})
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Add, ["nested"], None, {"a": 1})
            ]

            assert d == {"nested": {"a": 1}}
            assert d["nested"]._parent == d
            assert d["nested"]._reference_in_parent == "nested"

        def test_add_struct_as_nested_struct(self):
            d = ObservedDict(
                pre_callbacks=[pre_callback], post_callbacks=[post_callback]
            )
            d["nested"] = ObservedDict({"a": 1})

            assert pre_callback.call_args == [
                (d, ObservedOperation.Add, ["nested"], None, {"a": 1})
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Add, ["nested"], None, {"a": 1})
            ]

            assert d["nested"] == {"a": 1}
            assert d["nested"]._parent == d
            assert d["nested"]._reference_in_parent == "nested"

        def test_update_scalar_in_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            d["nested"]["a"] = 2

            assert pre_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Update, ["nested", "a"], 1, 2),
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Update, ["nested", "a"], 1, 2),
            ]

            assert d == {"nested": {"a": 2}}

        def test_update_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = d._struct["nested"]
            d["nested"] = {"b": 2}

            assert pre_callback.call_args == [
                (d, ObservedOperation.Update, ["nested"], {"a": 1}, {"b": 2})
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Update, ["nested"], {"a": 1}, {"b": 2})
            ]

            assert d == {"nested": {"b": 2}}
            assert d["nested"]._parent == d
            assert d["nested"]._reference_in_parent == "nested"
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_update_struct_as_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = d._struct["nested"]
            d["nested"] = ObservedDict({"b": 2})

            assert pre_callback.call_args == [
                (d, ObservedOperation.Update, ["nested"], {"a": 1}, {"b": 2})
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Update, ["nested"], {"a": 1}, {"b": 2})
            ]

            assert d == {"nested": {"b": 2}}
            assert d["nested"]._parent == d
            assert d["nested"]._reference_in_parent == "nested"
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_delete_scalar_from_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            del d["nested"]["a"]

            assert pre_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Remove, ["nested", "a"], 1, None),
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Remove, ["nested", "a"], 1, None),
            ]

            assert d == {"nested": {}}

        def test_delete_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = d._struct["nested"]
            del d["nested"]

            assert pre_callback.call_args == [
                (d, ObservedOperation.Remove, ["nested"], {"a": 1}, None)
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Remove, ["nested"], {"a": 1}, None)
            ]

            assert d == {}
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_access_scalar_in_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            assert d["nested"]["a"] == 1

            assert pre_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Access, ["nested", "a"], None, None),
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None),
                (d, ObservedOperation.Access, ["nested", "a"], None, None),
            ]

            assert d == {"nested": {"a": 1}}

        def test_access_to_nested_struct(self):
            d = ObservedDict(
                {"nested": {"a": 1}},
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            assert d["nested"] == {"a": 1}

            assert pre_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None)
            ]
            assert post_callback.call_args == [
                (d, ObservedOperation.Access, ["nested"], None, None)
            ]

            assert d == {"nested": {"a": 1}}


class TestObservedList:
    class TestInstantiation:
        def test_instantiation_without_arguments(self):
            s = ObservedList()
            assert s == []

        def test_instantiation_with_empty_list(self):
            s = ObservedList([])
            assert s == []

        def test_instantiation_with_list(self):
            s = ObservedList([1])
            assert s == [1]
            assert s[0] == 1

        def test_instantiation_with_another_observed_list(self):
            s = ObservedList(ObservedList([1]))
            assert s == [1]
            assert isinstance(s._struct, list)

        def test_instantion_with_nested_list(self):
            s = ObservedList([[1]])
            assert s == [[1]]
            assert s[0] == [1]
            assert s[0][0] == 1
            assert isinstance(s[0], ObservedList)
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0

        def test_instantiation_with_another_observed_struct_type(self):
            s = ObservedList([{"a": 1}])
            assert s == [{"a": 1}]
            assert s[0] == {"a": 1}
            assert isinstance(s[0], ObservedDict)
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0

    def comparison(self):
        s = ObservedList([[1, 2]])
        assert s == ObservedList([[1, 2]])
        assert s[0] == ObservedList([1, 2])
        assert s == ObservedList(ObservedList([1, 2]))
        assert s == [[1, 2]]
        assert s[0] == [1, 2]

    class TestListInterface:
        @pytest.fixture
        def s(self):
            return ObservedList([1, 2, 3])

        def test_length(self, s):
            assert len(s) == 3
            assert operator.length_hint(s) == 3

        def test_list(self, s):
            assert list(s) == [1, 2, 3]

        def test_iter(self, s):
            assert list(iter(s)) == [1, 2, 3]

        def test_membership(self, s):
            assert 1 in s
            assert 4 not in s

        def test_reversed(self, s):
            assert list(reversed(s)) == [3, 2, 1]

        def test_add(self, s):
            assert s + [4, 5] == [1, 2, 3, 4, 5]

        def test_extend(self, s):
            s.extend([4, 5])
            assert s == [1, 2, 3, 4, 5]

        def test_iadd(self, s):
            s += [4, 5]
            assert s == [1, 2, 3, 4, 5]

        class TestSlicing:
            def test_up_to(self, s):
                assert s[:1] == [1]

            def test_from(self, s):
                assert s[1:] == [2, 3]

            def test_interval(self, s):
                assert s[1:2] == [2]

            def test_step(self, s):
                assert s[::2] == [1, 3]

            def test_insert(self, s):
                s[1:2] = [7, 8, 9]
                assert s == [1, 7, 8, 9, 3]

            def test_del(self, s):
                del s[1:2]
                assert s == [1, 3]

            def test_insert_with_step(self, s):
                s[::2] = [4, 5]
                assert s == [4, 2, 5]

            def test_del_with_step(self, s):
                del s[::2]
                assert s == [2]

        def test_min(self, s):
            assert min(s) == 1

        def test_max(self, s):
            assert max(s) == 3

        def test_index(self, s):
            assert s.index(3, 1, 3) == 2

        def test_count(self, s):
            assert s.count(3) == 1

        def test_clear(self, s):
            s.clear()
            assert len(s) == 0

        def test_insert(self):
            s = ObservedList([])
            s.insert(0, 1)
            s.insert(0, 2)
            s.insert(0, 3)
            assert s == [3, 2, 1]

        def test_insert_last(self):
            s = ObservedList([])
            s.insert(10, 1)
            assert s == [1]

        def test_pop_position(self, s):
            s.pop(0)
            assert s == [2, 3]

        def test_pop_last(self, s):
            s.pop()
            assert s == [1, 2]

        def test_remove(self, s):
            s.remove(2)
            assert s == [1, 3]

        def test_reverse(self, s):
            s.reverse()
            assert s == [3, 2, 1]

    def test_resolve_slice_to_indexes(self):
        s = ObservedList([])
        assert list(s._resolve_slice_to_indexes(slice(0, 0))) == []
        assert list(s._resolve_slice_to_indexes(slice(0, 1))) == []
        assert list(s._resolve_slice_to_indexes(slice(0, 2))) == []

        s = ObservedList([1])
        assert list(s._resolve_slice_to_indexes(slice(0, 0))) == []
        assert list(s._resolve_slice_to_indexes(slice(0, 1))) == [0]
        assert list(s._resolve_slice_to_indexes(slice(0, 2, 2))) == [0]

        s = ObservedList([1, 2])
        assert list(s._resolve_slice_to_indexes(slice(0, 0))) == []
        assert list(s._resolve_slice_to_indexes(slice(0, 1))) == [0]
        assert list(s._resolve_slice_to_indexes(slice(0, 2))) == [0, 1]
        assert list(s._resolve_slice_to_indexes(slice(0, 2, 2))) == [0]
        assert list(s._resolve_slice_to_indexes(slice(0, 3))) == [0, 1]

    class TestScalars:
        def test_add(self):
            s = ObservedList(
                pre_callbacks=[pre_callback], post_callbacks=[post_callback]
            )
            s.append(1)

            assert pre_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, 1)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, 1)
            ]

            assert s == [1]

        def test_update(self):
            s = ObservedList(
                [1],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s[0] = 2

            assert pre_callback.call_args == [
                (s, ObservedOperation.Update, [0], 1, 2)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Update, [0], 1, 2)
            ]

            assert s == [2]

        def test_delete(self):
            s = ObservedList(
                [1],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            del s[0]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Remove, [0], 1, None)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Remove, [0], 1, None)
            ]

            assert s == []

        def test_access(self):
            s = ObservedList(
                [1],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            assert s[0] == 1

            assert pre_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None)
            ]

            assert s == [1]

    class TestNested:
        def test_append_scalar_to_nested_struct(self):
            s = ObservedList(
                [[]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s[0].append(1)

            assert pre_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Add, [0, 0], None, 1),
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Add, [0, 0], None, 1),
            ]

            assert s == [[1]]

        def test_append_nested_struct(self):
            s = ObservedList(
                pre_callbacks=[pre_callback], post_callbacks=[post_callback]
            )
            s.append([1])

            assert pre_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, [1])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, [1])
            ]

            assert s == [[1]]

        def test_append_struct_as_nested_struct(self):
            s = ObservedList(
                pre_callbacks=[pre_callback], post_callbacks=[post_callback]
            )
            s.append(ObservedList([1]))

            assert pre_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, [1])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, [1])
            ]

            assert s == [[1]]
            assert s[0]._parent == s
            assert s[0]._reference_in_parent == 0

        def test_update_scalar_in_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s[0][0] = 2

            assert pre_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Update, [0, 0], 1, 2),
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Update, [0, 0], 1, 2),
            ]

            assert s == [[2]]

        def test_update_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = s._struct[0]
            s[0] = [2]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Update, [0], [1], [2])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Update, [0], [1], [2])
            ]

            assert s == [[2]]
            assert s[0]._parent == s
            assert s[0]._reference_in_parent == 0
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_update_struct_as_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = s._struct[0]
            s[0] = ObservedList([2])

            assert pre_callback.call_args == [
                (s, ObservedOperation.Update, [0], [1], [2])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Update, [0], [1], [2])
            ]

            assert s == [[2]]
            assert s[0]._parent == s
            assert s[0]._reference_in_parent == 0
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_delete_scalar_from_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            del s[0][0]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Remove, [0, 0], 1, None),
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Remove, [0, 0], 1, None),
            ]

            assert s == [[]]

        def test_delete_nested_struct(self):
            s = ObservedList(
                [[1], [2]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = s._struct[0]
            del s[0]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Remove, [0], [1], None)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Remove, [0], [1], None)
            ]

            assert s == [[2]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_delete_nested_struct_with_slice(self):
            s = ObservedList(
                [[1], [2]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            old_struct = s._struct[0]
            del s[0:1]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Remove, [0], [1], None)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Remove, [0], [1], None)
            ]

            assert s == [[2]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert old_struct._parent is None
            assert old_struct._reference_in_parent is None

        def test_access_scalar_in_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            assert s[0][0] == 1

            assert pre_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Access, [0, 0], None, None),
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None),
                (s, ObservedOperation.Access, [0, 0], None, None),
            ]

            assert s == [[1]]

        def test_access_to_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            assert s[0] == [1]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Access, [0], None, None)
            ]

            assert s == [[1]]

        def test_add_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s = s + [[2]]

            assert pre_callback.call_args == []
            assert post_callback.call_args == []

            assert s == [[1], [2]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert s[1]._parent is s
            assert s[1]._reference_in_parent == 1

        def test_iadd_nested_struct(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s += [[2]]

            assert pre_callback.call_args == [
                (s, ObservedOperation.Add, [1], None, [2])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Add, [1], None, [2])
            ]

            assert s == [[1], [2]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert s[1]._parent is s
            assert s[1]._reference_in_parent == 1

        def test_extend(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s.extend([[2]])

            assert pre_callback.call_args == [
                (s, ObservedOperation.Add, [1], None, [2])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Add, [1], None, [2])
            ]

            assert s == [[1], [2]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert s[1]._parent is s
            assert s[1]._reference_in_parent == 1

        def test_insert(self):
            s = ObservedList(
                [[1]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s.insert(0, [0])

            assert pre_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, [0])
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Add, [0], None, [0])
            ]

            assert s == [[0], [1]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert s[1]._parent is s
            assert s[1]._reference_in_parent == 1

        def test_pop(self):
            s = ObservedList(
                [[1], [2]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s.pop(0)

            assert pre_callback.call_args == [
                (s, ObservedOperation.Remove, [0], [1], None)
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Remove, [0], [1], None)
            ]

            assert s == [[2]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0

        def test_reverse(self):
            s = ObservedList(
                [[1], [2]],
                pre_callbacks=[pre_callback],
                post_callbacks=[post_callback],
            )
            s.reverse()

            assert pre_callback.call_args == [
                (s, ObservedOperation.Update, [0], [1], [2]),
                (s, ObservedOperation.Update, [1], [2], [1]),
            ]
            assert post_callback.call_args == [
                (s, ObservedOperation.Update, [0], [1], [2]),
                (s, ObservedOperation.Update, [1], [2], [1]),
            ]

            assert s == [[2], [1]]
            assert s[0]._parent is s
            assert s[0]._reference_in_parent == 0
            assert s[1]._parent is s
            assert s[1]._reference_in_parent == 1


class TestInterfaceAcrossClasses:
    def test_list_in_dict(self):
        d = ObservedDict(
            {"a": [1]},
            pre_callbacks=[pre_callback],
            post_callbacks=[post_callback],
        )
        assert d["a"][0] == 1

        assert pre_callback.call_args == [
            (d, ObservedOperation.Access, ["a"], None, None),
            (d, ObservedOperation.Access, ["a", 0], None, None),
        ]
        assert post_callback.call_args == [
            (d, ObservedOperation.Access, ["a"], None, None),
            (d, ObservedOperation.Access, ["a", 0], None, None),
        ]

        assert d == {"a": [1]}

    def test_dict_in_list(self):
        s = ObservedList(
            [{"a": 1}],
            pre_callbacks=[pre_callback],
            post_callbacks=[post_callback],
        )
        assert s[0]["a"] == 1

        assert pre_callback.call_args == [
            (s, ObservedOperation.Access, [0], None, None),
            (s, ObservedOperation.Access, [0, "a"], None, None),
        ]
        assert post_callback.call_args == [
            (s, ObservedOperation.Access, [0], None, None),
            (s, ObservedOperation.Access, [0, "a"], None, None),
        ]

        assert s == [{"a": 1}]
