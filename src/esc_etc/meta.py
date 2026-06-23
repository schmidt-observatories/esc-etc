"""Mutable-parameter base class shared by ESC ETC components.

Mirrors the wcc-etc _MetaHolder_ pattern (copied, not imported): each subclass
declares ``_mutable_parameters`` and stores its initial values with
``_init_meta``. ``update`` supports nested ``child__param=`` routing.
"""


class _MetaHolder_:
    def _init_meta(self, **kwargs):
        if not hasattr(self, "_mutable_parameters"):
            self._mutable_parameters = list(kwargs.keys())
        self.meta = dict(kwargs)
        self._initial = dict(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def update(self, **kwargs):
        updated = []
        for key, value in kwargs.items():
            if "__" in key:
                child_name, sub_key = key.split("__", 1)
                child = getattr(self, child_name)
                updated += [f"{child_name}__{k}" for k in child.update(**{sub_key: value})]
                continue
            if key not in self._mutable_parameters:
                raise KeyError(
                    f"{key!r} is not a mutable parameter of {type(self).__name__}; "
                    f"allowed: {self._mutable_parameters}"
                )
            setattr(self, key, value)
            self.meta[key] = value
            updated.append(key)
        self._on_update(updated)
        return updated

    def reset(self):
        for key, value in self._initial.items():
            setattr(self, key, value)
            self.meta[key] = value
        self._on_update(list(self._initial.keys()))

    def describe(self):
        for key in self._mutable_parameters:
            print(f"{key} = {getattr(self, key, None)}")

    def _on_update(self, updated_keys):
        """Hook for cache invalidation; overridden where caching exists."""
        pass
