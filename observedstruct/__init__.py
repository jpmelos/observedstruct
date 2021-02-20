import enum
import sys


class ObservedOperation(enum.Enum):
    Add = "add"
    Update = "update"
    Remove = "remove"
    Access = "access"


class CallbackType(enum.Enum):
    Pre = "pre"
    Post = "post"


def get_item_for_reference(d, path):
    if len(path) > 1:
        return get_item_for_reference(d._struct[path[0]], path[1:])
    return d._struct[path[0]]


def get_observable_struct(value, parent, reference_in_parent):
    if isinstance(value, dict):
        return ObservedDict(
            value, parent=parent, reference_in_parent=reference_in_parent
        )
    if isinstance(value, list):
        return ObservedList(
            value, parent=parent, reference_in_parent=reference_in_parent
        )
    if isinstance(value, ObservedStruct):
        value._parent = parent
        value._reference_in_parent = reference_in_parent
    return value


def make_root_struct(value):
    if isinstance(value, ObservedStruct):
        value._parent = None
        value._reference_in_parent = None
    return value


class ObservedStruct:
    _base_type = None

    def __init__(
        self,
        initial=None,
        *,
        pre_callbacks=None,
        post_callbacks=None,
        parent=None,
        reference_in_parent=None,
    ):
        if initial is None:
            initial = self._base_type()
        if pre_callbacks is None:
            pre_callbacks = []
        if post_callbacks is None:
            post_callbacks = []

        if not isinstance(
            initial, (type(self), self._base_type)
        ):  # pragma: no cover
            raise ValueError(
                f"{type(self).__name__} expects a"
                f" `{self._base_type.__name__}` or another"
                f" `{type(self).__name__}` for initialization"
            )
        if isinstance(initial, self._base_type):
            self._process_initial(initial)

        if isinstance(initial, type(self)):
            self._struct = initial._struct
        else:
            self._struct = initial
        self._pre_callbacks = pre_callbacks
        self._post_callbacks = post_callbacks
        self._parent = parent
        self._reference_in_parent = reference_in_parent

    def __len__(self):
        return len(self._struct)

    def __iter__(self):
        return iter(self._struct)

    def __contains__(self, item):
        return item in self._struct

    def __reversed__(self):
        return reversed(self._struct)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self._struct == other._struct
        if isinstance(other, self._base_type):
            return self._struct == other
        return NotImplemented  # pragma: no cover

    def __str__(self):  # pragma: no cover
        return str(self._struct)

    def __repr__(self):  # pragma: no cover
        return f"{type(self).__name__}({repr(self._struct)})"

    def _process_initial(self, initial):  # pragma: no cover
        raise NotImplementedError

    def _process_callbacks(
        self, callback_type, operation, reference, old_value, new_value
    ):
        if self._parent:
            path_in_parent = [self._reference_in_parent, *reference]
            self._parent._process_callbacks(
                callback_type, operation, path_in_parent, old_value, new_value
            )
        else:
            if callback_type == CallbackType.Pre:
                callbacks = self._pre_callbacks
            else:
                callbacks = self._post_callbacks
            for callback in callbacks:
                callback(self, operation, reference, old_value, new_value)


class ObservedDict(ObservedStruct):
    _base_type = dict

    def _process_initial(self, initial):
        for key, value in initial.items():
            initial[key] = get_observable_struct(
                value, parent=self, reference_in_parent=key
            )

    if sys.version_info < (3, 8):  # pragma: no cover

        def __reversed__(self):
            return reversed(list(self._struct.keys()))

    def __or__(self, other):
        return ObservedDict(
            {
                **{key: value for key, value in self.items()},
                **{key: value for key, value in other.items()},
            }
        )

    def __ior__(self, other):
        self.update(other)
        return self

    def __getitem__(self, key):
        self._process_callbacks(
            CallbackType.Pre, ObservedOperation.Access, [key], None, None
        )
        rv = self._struct[key]
        self._process_callbacks(
            CallbackType.Post, ObservedOperation.Access, [key], None, None
        )
        return rv  # noqa: R504

    def __setitem__(self, key, value):
        if key in self._struct:
            operation = ObservedOperation.Update
            old_value = self._struct[key]
        else:
            operation = ObservedOperation.Add
            old_value = None
        new_value = get_observable_struct(
            value, parent=self, reference_in_parent=key
        )

        self._process_callbacks(
            CallbackType.Pre, operation, [key], old_value, new_value
        )
        self._struct[key] = new_value
        make_root_struct(old_value)
        self._process_callbacks(
            CallbackType.Post, operation, [key], old_value, new_value
        )

    def __delitem__(self, key):
        old_value = self._struct[key]
        self._process_callbacks(
            CallbackType.Pre, ObservedOperation.Remove, [key], old_value, None
        )
        del self._struct[key]
        make_root_struct(old_value)
        self._process_callbacks(
            CallbackType.Post, ObservedOperation.Remove, [key], old_value, None
        )

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return self._struct.keys()

    def values(self):
        for key in self:
            yield self[key]

    def items(self):
        for key in self:
            yield key, self[key]

    def pop(self, key, default=None):
        try:
            rv = self[key]
            del self[key]
            return rv  # noqa: R504
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def popitem(self):
        try:
            key = list(self.keys())[-1]
            value = self[key]
            del self[key]
            return key, value
        except IndexError:
            raise KeyError

    def update(self, other):
        for key, value in other.items():
            self[key] = value

    def clear(self):
        for key in list(self):
            del self[key]


class ObservedList(ObservedStruct):
    _base_type = list

    def _resolve_slice_to_indexes(self, slice_obj):
        start = 0
        if slice_obj.start is not None:
            start = slice_obj.start

        stop = len(self)
        if slice_obj.stop is not None:
            stop = min(slice_obj.stop, len(self))

        step = 1
        if slice_obj.step is not None:
            step = slice_obj.step

        if start == stop:
            return

        yv = start
        yield yv
        yv += step
        while yv < stop:
            yield yv
            yv += step

    def _process_initial(self, initial):
        for index, value in enumerate(initial):
            initial[index] = get_observable_struct(
                value, parent=self, reference_in_parent=index
            )

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._get_for_slice(index)
        return self._get_for_index(index)

    def _get_for_index(self, index):
        self._process_callbacks(
            CallbackType.Pre, ObservedOperation.Access, [index], None, None
        )
        rv = self._struct[index]
        self._process_callbacks(
            CallbackType.Post, ObservedOperation.Access, [index], None, None
        )
        return rv  # noqa: R504

    def _get_for_slice(self, slice_):
        indexes = self._resolve_slice_to_indexes(slice_)
        rv = []
        for index in indexes:
            rv.append(self._get_for_index(index))
        return rv

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            return self._set_for_slice(index, value)
        return self._set_for_index(index, value)

    def _set_for_index(self, index, value):
        operation = ObservedOperation.Update
        old_value = self._struct[index]
        new_value = get_observable_struct(
            value, parent=self, reference_in_parent=index
        )

        self._process_callbacks(
            CallbackType.Pre, operation, [index], old_value, new_value
        )
        self._struct[index] = new_value
        make_root_struct(old_value)
        self._process_callbacks(
            CallbackType.Post, operation, [index], old_value, new_value
        )

    def _set_for_slice(self, slice_, values):
        if slice_.step in [None, 1]:
            self._set_for_contiguous_space(slice_, values)
        else:
            self._set_for_non_contiguous_space(slice_, values)

    def _set_for_contiguous_space(self, slice_, values):
        indexes = self._resolve_slice_to_indexes(slice_)
        for index in indexes:
            del self[index]
        self._struct[slice_.start : slice_.start] = [None] * len(values)
        for delta, value in enumerate(values):
            self[slice_.start + delta] = value

    def _set_for_non_contiguous_space(self, slice_, values):
        positions = list(self._resolve_slice_to_indexes(slice_))

        if len(positions) != len(values):  # pragma: no cover
            # Raise the same error the normal operation would
            self._struct[slice_] = values

        for position, value in zip(positions, values):
            self[position] = value

    def __delitem__(self, index):
        if isinstance(index, slice):
            self._del_item_for_slice(index)
            return
        self._del_item_for_index(index)

    def _del_item_for_index(self, index):
        old_position = index
        old_value = self._struct[index]

        self._process_callbacks(
            CallbackType.Pre,
            ObservedOperation.Remove,
            [old_position],
            old_value,
            None,
        )

        del self._struct[index]
        make_root_struct(old_value)
        for index, item in enumerate(self._struct[index:]):
            if isinstance(item, ObservedStruct):
                item._reference_in_parent = index

        self._process_callbacks(
            CallbackType.Post,
            ObservedOperation.Remove,
            [old_position],
            old_value,
            None,
        )

    def _del_item_for_slice(self, slice_):
        indexes = self._resolve_slice_to_indexes(slice_)
        for subtractor, index in enumerate(indexes):
            old_value = self._struct[index - subtractor]

            self._process_callbacks(
                CallbackType.Pre,
                ObservedOperation.Remove,
                [index - subtractor],
                old_value,
                None,
            )

            del self._struct[index - subtractor]
            make_root_struct(old_value)
            for index, item in enumerate(self._struct[index - subtractor :]):
                if isinstance(item, ObservedStruct):
                    item._reference_in_parent = index

            self._process_callbacks(
                CallbackType.Post,
                ObservedOperation.Remove,
                [index - subtractor],
                old_value,
                None,
            )

    def __add__(self, other):
        return ObservedList([*self, *other])

    def __iadd__(self, other):
        for item in other:
            self.append(item)
        return self

    def append(self, value):
        operation = ObservedOperation.Add
        old_value = None
        new_index = len(self._struct)
        new_value = get_observable_struct(
            value, parent=self, reference_in_parent=new_index
        )

        self._process_callbacks(
            CallbackType.Pre, operation, [new_index], old_value, new_value
        )
        self._struct.append(new_value)
        self._process_callbacks(
            CallbackType.Post, operation, [new_index], old_value, new_value
        )

    def extend(self, other):
        for item in other:
            self.append(item)

    def index(self, value, start, end):
        return self._struct.index(value, start, end)

    def count(self, value):
        return self._struct.count(value)

    def insert(self, position, value):
        if len(self) <= position:
            self.append(value)
            return

        new_value = get_observable_struct(
            value, parent=self, reference_in_parent=position
        )

        self._process_callbacks(
            CallbackType.Pre,
            ObservedOperation.Add,
            [position],
            None,
            new_value,
        )
        self._struct[position : position + 1] = [
            new_value,
            self._struct[position],
        ]
        for index, item in enumerate(self._struct[position + 1 :]):
            if isinstance(item, ObservedStruct):
                item._reference_in_parent = position + 1 + index
        self._process_callbacks(
            CallbackType.Post,
            ObservedOperation.Add,
            [position],
            None,
            new_value,
        )

    def remove(self, value):
        for index, item in enumerate(self):
            if item == value:
                self.pop(index)

    def pop(self, position=None, default=None):
        if position is None:
            position = len(self) - 1

        try:
            rv = self._struct[position]
            del self[position]
            if position < len(self):
                for index, item in enumerate(self._struct[position - 1 :]):
                    if isinstance(item, ObservedStruct):
                        item._reference_in_parent = index
            return rv  # noqa: R504
        except IndexError:  # pragma: no cover
            return default

    def reverse(self):
        operation = ObservedOperation.Update

        for first_index in range(len(self) // 2):
            first_value = self._struct[first_index]
            last_index = len(self._struct) - first_index - 1
            last_value = self._struct[last_index]
            self._process_callbacks(
                CallbackType.Pre,
                operation,
                [first_index],
                first_value,
                last_value,
            )
            self._process_callbacks(
                CallbackType.Pre,
                operation,
                [last_index],
                last_value,
                first_value,
            )

        self._struct.reverse()

        for index, item in enumerate(self._struct):
            if isinstance(item, ObservedStruct):
                item._reference_in_parent = index

        for last_index in range(len(self) // 2):
            first_index = len(self._struct) - last_index - 1
            first_value = self._struct[first_index]
            last_value = self._struct[last_index]
            self._process_callbacks(
                CallbackType.Post,
                operation,
                [last_index],
                first_value,
                last_value,
            )
            self._process_callbacks(
                CallbackType.Post,
                operation,
                [first_index],
                last_value,
                first_value,
            )

    def clear(self):
        while len(self) > 0:
            self.pop()
