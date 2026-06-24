# Custom Dumper & Validator

A simple, fast, and efficient Python tool designed to serialize (dump) complex, nested Python objects into native data types and validate them into target class entities.

### Why is this better than `dataclasses.asdict`?
1. **Property Support:** It dynamically evaluates and extracts data from public `@property` methods.
2. **Versatility:** It can dump (almost) any standard Python object, not just structured dataclasses.
3. **Graph-Safe (Circular Dependency Protection):** It tracks the execution stack to gracefully handle cyclic references and interconnected graphs without blowing up the call stack with a `RecursionError`.

---

## Use Cases

### 1. Fast Object Dumping with Properties

```python
from dumper import Dumper

class User:
    def __init__(self, first_name: str, last_name: str):
        self.first_name = first_name
        self.last_name = last_name
        self._token = "secret_key"  # This will be ignored

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

user = User("Gleb", "Ivanov")
dumped_data = Dumper.dump(user)

print(dumped_data)
# Output: {'first_name': 'Gleb', 'last_name': 'Ivanov', 'full_name': 'Gleb Ivanov'}
```

### 2. Data validation

```python
from dumper import ValidationEntity

class TargetUser(ValidationEntity):
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

# Imagine some arbitrary third-party object or mock data
class ExternalData:
    def __init__(self):
        self.name = "Alice"
        self.age = 25

# Validate and automatically instantiate TargetUser
validated_user = TargetUser.validate(ExternalData())
print(isinstance(validated_user, TargetUser))  # True
```


### 3. Handling Cyclic Graphs

```python
# Default safe behavior (prevents infinite recursion loops)
dumped_graph = Dumper.dump(cyclic_node, deep=False)
```
