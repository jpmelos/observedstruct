# observedstruct

Observed structures that calls your functions on changes.

## Install

`observedstruct` supports Python 3.7, 3.8, and 3.9.

```
pip install observedstruct
```

## API

### `observedstruct.ObservedOperation`

These are the operations tracked by the structures:

- `ObservedOperation.Access`
- `ObservedOperation.Add`
- `ObservedOperation.Update`
- `ObservedOperation.Remove`

These values are sent to the callbacks.

### `get_item_for_reference(struct, reference)`

Find an item inside a structure based on a reference list.

### `observedstruct.ObservedDict`

- `__init__(initial, *, pre_callbacks=None, post_callbacks=None)`

`ObservedDict` can be instantiated with another `dict`, and it will recursively turn all nested dictionaries and lists into observed structs as well (by using `ObservedDict` and `ObservedList`). `pre_callbacks` are functions to be called before an operation takes place, and `post_callbacks` are functions to be called after an operation takes place.

```python
from observedstruct import ObservedDict

def pre_callback(struct, operation, reference, old_value, new_value):
    pass

def post_callback(struct, operation, reference, old_value, new_value):
    pass

d = ObservedDict(
    {'a': 1},
    pre_callbacks=[pre_callback],
    post_callbacks=[post_callback],
)
d['b'] = 2
```

Callbacks are called with:

- `struct`: The structure in which the event is taking place. You can find the affected object in the structure by navigating to the reference list in `reference` starting from the `struct`.
- `operation`: One of `ObservedOperation`.
- `reference`: A list of references inside the structure that can be used to find the affected object. If the structure is a list, it will be an integer, and if it's a dictionary, it will the object used as key. It can be something like `['a', 0]` for a dictionary that contains key `a` which is a list, and the operation takes place at the first position in the list. You can use the utility function `get_item_for_reference` to find the object the reference refers to from inside callback functions.
- `old_value`: The value that will be removed from the structure.
- `new_value`: The value that will be added to the structure.

This class supports all operations a regular dictionary supports.

### `observedstruct.ObservedList`

Same as the `ObservedDict` class, but you instantiate this class with a `list`.

## Limitations

An observed structure can only belong inside one other observed structure. To allow for the callback functions to be found and to be called with the correct references, each nested observed structure stores a reference to its parent and where it can be found in the parent. If an observed structure belongs to more than one parent, then it will have those attributes replaced and one of the parents won't be reachable from the child.

Callbacks registered in nested structures will not be called. Once a structure belongs in another structure, only the callbacks from the root structure in the hierarchy are called. Because of this, the multiplication of lists does not work in `ObservedList`, since that would make several instances of a nested structure happen inside a list, and the reference would be wrong for at least one of the occurrences.

## Development

Clone the source code from GitHub, have all supported Python interpreters in your `PATH` (we recommend that you use `pyenv` to manage different Python interpreters and environments) and create a new virtual environment with `poetry install`.

Run the tests with:

```
./run all-tests
```

To run a specific test:

```
./run test <test-address>
```

To make sure your code complies with our quality standards, run:

```
./run quality
```
