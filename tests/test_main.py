import pytest
from typing import Any

from src.main import Validator, Dumper


class SimpleUser:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
        self._token = "secret_123"  # Приватный атрибут

    def get_version(self):  # Обычный метод
        return "1.0.0"


class PropertyUser:
    def __init__(self, first_name: str, last_name: str):
        self.first_name = first_name
        self.last_name = last_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def _crypto_wallet(self) -> str:  # Приватное свойство
        return "0x123..."


class Node:
    def __init__(self, value: Any):
        self.value = value
        self.left = None
        self.right = None


class DynamicCallable:
    def __init__(self):
        self.status = "active"
        # Динамически привязанная функция прямо в инстанс
        self.callback = lambda x: x * 2


class ValidatedTarget(Validator):
    name: str
    age: str


def test_dump_primitives():
    """Проверяем, что базовые типы возвращаются как есть, без изменений."""
    assert Dumper.dump(100) == 100
    assert Dumper.dump("python") == "python"
    assert Dumper.dump(5.5) == 5.5
    assert Dumper.dump(True) is True
    assert Dumper.dump(None) is None


def test_dump_collections_type_saving():
    """Проверяем коллекции. Исходный тип (list, tuple, set) должен сохраняться."""
    assert Dumper.dump([1, 2, 3]) == [1, 2, 3]
    assert Dumper.dump((1, 2, 3)) == (1, 2, 3)
    assert Dumper.dump({1, 2, 3}) == {1, 2, 3}
    assert Dumper.dump(frozenset([1, 2])) == frozenset([1, 2])


def test_dump_nested_dict():
    """Проверяем честный обход стандартных словарей любой вложенности."""
    data = {"user": "admin", "meta": {"roles": ["root", "user"], "active": True}}
    assert Dumper.dump(data) == data


def test_dump_custom_class_filtering():
    """Проверяем, что методы и приватные поля вырезаются, а публичные остаются."""
    user = SimpleUser("Gleb", 29)
    result = Dumper.dump(user)

    assert result == {"name": "Gleb", "age": 29}
    assert "_token" not in result
    assert "get_version" not in result


def test_dump_properties_processing():
    """Проверяем, что публичные @property вычисляются, а приватные — игнорируются."""
    user = PropertyUser("Ivan", "Ivanov")
    result = Dumper.dump(user)

    assert result == {
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "full_name": "Ivan Ivanov",
    }
    assert "_crypto_wallet" not in result


def test_dump_dynamic_callable_in_dict():
    """Проверяем, что callable-объекты, зашитые прямо в __dict__ инстанса, не дампятся."""
    obj = DynamicCallable()
    result = Dumper.dump(obj)

    assert result == {"status": "active"}
    assert "callback" not in result


def test_dump_diamond_graph_cpu_optimization():
    """Проверяем мемоизацию (кэш processed).

    Если один объект лежит в разных ветках, он должен вычислиться 1 раз
    и вернуть идентичные ссылки.
    """
    shared_node = SimpleUser("Shared", 42)
    graph = {"node_left": shared_node, "node_right": shared_node}

    result = Dumper.dump(graph)

    assert result["node_left"] is result["node_right"]
    assert result["node_left"] == {"name": "Shared", "age": 42}


def test_dump_cyclic_graph_prevents_recursion():
    """При deep=False циклические ссылки должны обрываться, защищая стек от переполнения."""
    node_a = Node("A")
    node_b = Node("B")

    node_a.left = node_b
    node_b.right = node_a  # Образовался цикл: A -> B -> A

    result = Dumper.dump(node_a, deep=False)

    assert result["value"] == "A"
    assert result["left"]["value"] == "B"
    # На узле B ссылка обратно на A была пропущена детектором циклов
    assert "right" not in result["left"]


def test_dump_cyclic_graph_deep_raises_recursion_error():
    """При deep=True детектор циклов отключается, на зацикленном графе мы обязаны упасть."""
    node_a = Node("A")
    node_b = Node("B")
    node_a.left = node_b
    node_b.right = node_a

    with pytest.raises(RecursionError):
        Dumper.dump(node_a, deep=True)


def test_validation_entity_success():
    """Проверяем успешный проход валидации."""
    source_data = SimpleUser("Alice", 23)

    # Кастомный объект превращается в дамп и успешно разворачивается в конструктор ValidatedTarget
    instance = ValidatedTarget.validate(source_data)

    assert isinstance(instance, ValidatedTarget)
    assert instance.name == "Alice"
    assert instance.age == 23


def test_validation_entity_invalid_attributes():
    """Проверяем падение валидации с кастомным исключением при несовпадении полей."""
    # У PropertyUser поля first_name и last_name, а ValidatedTarget ждет name и age
    invalid_source = PropertyUser("John", "Doe")

    with pytest.raises(Exception) as exc_info:
        ValidatedTarget.validate(invalid_source)


def test_validator_meta_positional_args():
    """Проверяем, что метакласс корректно собирает объект через позиционные аргументы."""
    # Передаем строго по порядку: name, затем age
    instance = ValidatedTarget("Gleb", 29)

    assert instance.name == "Gleb"
    assert instance.age == 29


def test_validator_meta_missing_arguments_raises_type_error():
    """Проверяем, что если не передать обязательное поле, вылетает TypeError."""
    # Пропустили поле 'age'
    with pytest.raises(TypeError) as exc_info:
        ValidatedTarget(name="Anatoliy")

    assert "missing required arguments: age" in str(exc_info.value)


def test_validator_meta_extra_arguments_raises_type_error():
    """Проверяем, что передача неаннотированного мусора пресекается конструктором."""
    # Передали 'hobby', которого нет в классе ValidatedTarget
    with pytest.raises(TypeError) as exc_info:
        ValidatedTarget(name="Ivan", age=20, hobby="coding")

    assert "got unexpected keyword arguments: hobby" in str(exc_info.value)


def test_validator_meta_mixed_args_and_kwargs():
    """Проверяем совмещенный вариант (часть через args, часть через kwargs)."""
    # 'Gleb' пойдет в name (первая аннотация), age передаем явно
    instance = ValidatedTarget("Gleb", age=29)

    assert instance.name == "Gleb"
    assert instance.age == 29


def test_validator_meta_positional_overflow_raises_type_error():
    """Проверяем, что передача лишних позиционных аргументов валит конструктор."""
    # Передали 3 аргумента вместо 2 допустимых
    with pytest.raises(TypeError) as exc_info:
        ValidatedTarget("Gleb", 29, "ExtraArg")

    assert "positional arguments but more were given" in str(exc_info.value)
