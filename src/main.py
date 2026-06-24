from typing import Self, Any


class Dumper:
    _dump_processed = dict()  # ids of processed objects
    _dump_linked = set()  # ids of object in processing
    _dump_deep: bool = False

    class NotFound:
        pass  # for "correct checking" for the non existed fields

    @classmethod
    def _dump_process_dict(cls, obj) -> dict:
        return {
            k: cls._inner_dump(v)
            for k, v in obj.items()
            if id(v) not in cls._dump_linked
        }

    @classmethod
    def _dump_process_dict_attrs(cls, obj) -> dict:
        keys: set = set()

        # adding class'es properties to the keys
        if hasattr(type(obj), "__dict__"):
            for pr_name in type(obj).__dict__.keys():
                # only properties
                if not isinstance(getattr(type(obj), pr_name), property):
                    continue

                # excludint private and protected properties
                if pr_name.startswith("_"):
                    continue

                # adding correct one to the keys
                keys.add(pr_name)

        # adding objects attributes
        for key in obj.__dict__.keys():
            # skipping private and protected
            if key.startswith("_"):
                continue

            value = getattr(obj, key)

            # skipping methods
            if callable(value):
                continue

            keys.add(key)

        result = {}

        for k in keys:
            temp_value = getattr(obj, k)

            # skipping if value is already processing
            if id(temp_value) in cls._dump_linked:
                continue

            result[k] = cls._inner_dump(temp_value)

        return result

    @classmethod
    def _dump_process_list_like_obj(cls, obj):
        # processing obj with type saving

        return type(obj)(
            cls._inner_dump(el) for el in obj if id(el) not in cls._dump_linked
        )

    @classmethod
    def _inner_dump(cls, obj) -> dict:
        if cls._dump_deep is False:
            # adding only to avoid recursion errors
            cls._dump_linked.add(id(obj))  # adding obj id to linked set

        # do not process already processed obj, just return the link to it
        if cls._dump_processed.get(id(obj), cls.NotFound) is not cls.NotFound:
            return cls._dump_processed.get(id(obj))

        level_dump_result: Any = object()

        if isinstance(obj, (tuple, list, set, frozenset)):
            level_dump_result = cls._dump_process_list_like_obj(obj)
        elif isinstance(obj, dict):
            level_dump_result = cls._dump_process_dict(obj)
        elif hasattr(obj, "__dict__"):
            level_dump_result = cls._dump_process_dict_attrs(obj)
        else:
            level_dump_result = obj

        # saving link to the result of the level dump
        # to return it without processing later
        if id(obj) in cls._dump_linked:
            # remove id of the obj from links
            cls._dump_linked.remove(id(obj))

        cls._dump_processed[id(obj)] = level_dump_result
        return level_dump_result

    @classmethod
    def dump(cls, obj, deep: bool = False) -> Any:
        """
        Why is this better then asdict from dataclasses?
        1. Properties. Asdict cannot process properties
        2. This method can dump (almost) any python object
        3. Asdict cannot process graphs because of recursion error

        obj: object to get a dump
        deep: flag for recursive links. If False - function will
        skip the cycle links to avoid recursion. Default state.
        """

        cls._dump_processed = dict()  # ids of processed objects
        cls._dump_linked = set()  # ids of object in processing
        cls._dump_deep = deep

        return cls._inner_dump(obj)


class Validator(Dumper):
    @classmethod
    def validate(cls, to_validate: dict[str, Any] | Any) -> Self:
        """
        Validate any python object to the entry of this class.
        Usage:
            obj: MyClassWithValidator = MyClassWithValidator.validate(any_python_object)

        :to_validate - dict[str, Any] whem from_attribute is False or not set.
        :from_attribute - bool, use to change to_validate type
            (dict for False, or Any for True)
        """

        validation_dict: dict = cls.dump(to_validate)

        try:
            return cls(**validation_dict)
        except TypeError:
            raise Exception(f"Attribures are incorrect. Got {validation_dict}")
