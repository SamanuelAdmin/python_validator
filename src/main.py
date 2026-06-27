import inspect
from typing import Self, Any, dataclass_transform


@dataclass_transform()
class ValidatorMeta(type):
    def __new__(cls, name, bases, dct):
        new_class = super().__new__(cls, name, bases, dct)

        annotations = {}
        for base in reversed(inspect.getmro(new_class)):
            if hasattr(base, "__annotations__"):
                annotations.update(base.__annotations__)

        def __init__(self, *args, **kwargs):
            field_names = list(annotations.keys())
            provided_kwargs = kwargs.copy()

            for i, arg in enumerate(args):
                if i < len(field_names):
                    provided_kwargs[field_names[i]] = arg
                else:
                    raise TypeError(
                        f"__init__() takes {len(field_names)} positional arguments but more were given"
                    )

            missing_fields = [f for f in field_names if f not in provided_kwargs]
            if missing_fields:
                raise TypeError(
                    f"__init__() missing required arguments: {', '.join(missing_fields)}"
                )

            extra_fields = [f for f in provided_kwargs if f not in field_names]
            if extra_fields:
                raise TypeError(
                    f"__init__() got unexpected keyword arguments: {', '.join(extra_fields)}"
                )

            for field_name, value in provided_kwargs.items():
                setattr(self, field_name, value)

        new_class.__init__ = __init__
        return new_class


class Dumper:
    _dump_processed = dict()
    _dump_linked = set()
    _dump_deep = False

    class NotFound:
        pass

    @classmethod
    def _dump_process_dict(cls, obj) -> dict:
        return {
            k: cls._inner_dump(v)
            for k, v in obj.items()
            if id(v) not in cls._dump_linked
        }

    @classmethod
    def _dump_process_dict_attrs(cls, obj) -> dict:
        keys = set()
        if hasattr(type(obj), "__dict__"):
            for pr_name in type(obj).__dict__.keys():
                if not isinstance(getattr(type(obj), pr_name), property):
                    continue
                if pr_name.startswith("_"):
                    continue
                keys.add(pr_name)

        for key in obj.__dict__.keys():
            if key.startswith("_"):
                continue
            value = getattr(obj, key)
            if callable(value):
                continue
            keys.add(key)

        result = {}
        for k in keys:
            temp_value = getattr(obj, k)
            if id(temp_value) in cls._dump_linked:
                continue
            result[k] = cls._inner_dump(temp_value)
        return result

    @classmethod
    def _dump_process_list_like_obj(cls, obj):
        return type(obj)(
            cls._inner_dump(el) for el in obj if id(el) not in cls._dump_linked
        )

    @classmethod
    def _inner_dump(cls, obj) -> dict:
        if cls._dump_deep is False:
            cls._dump_linked.add(id(obj))
        if cls._dump_processed.get(id(obj), cls.NotFound) is not cls.NotFound:
            return cls._dump_processed.get(id(obj))

        if isinstance(obj, (tuple, list, set, frozenset)):
            level_dump_result = cls._dump_process_list_like_obj(obj)
        elif isinstance(obj, dict):
            level_dump_result = cls._dump_process_dict(obj)
        elif hasattr(obj, "__dict__"):
            level_dump_result = cls._dump_process_dict_attrs(obj)
        else:
            level_dump_result = obj

        if id(obj) in cls._dump_linked:
            cls._dump_linked.remove(id(obj))

        cls._dump_processed[id(obj)] = level_dump_result
        return level_dump_result

    @classmethod
    def dump(cls, obj, deep: bool = False) -> Any:
        cls._dump_processed = dict()
        cls._dump_linked = set()
        cls._dump_deep = deep
        return cls._inner_dump(obj)


class Validator(Dumper, metaclass=ValidatorMeta):
    @classmethod
    def validate(cls, to_validate: dict[str, Any] | Any) -> Self:
        validation_dict: dict = cls.dump(to_validate)

        if not isinstance(validation_dict, dict):
            raise Exception(
                f"Validation source must be dumpable to dict. Got {type(to_validate)}"
            )

        try:
            return cls(**validation_dict)
        except TypeError as e:
            raise Exception(
                f"Attributes are incorrect. Got {validation_dict}. Inner error: {e}"
            )
