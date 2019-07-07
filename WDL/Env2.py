"""
Environments for namespaced identifier resolution during WDL typechecking and evaluation.
"""
from typing import TypeVar, Generic, Optional, Callable, Iterator, Dict, Set

T = TypeVar("T")
S = TypeVar("S")


class Base(Generic[T]):
    """
    ``WDL.Env.Base`` is the generic data structure for an environment binding names onto some
    associated values. WDL names are unique, and may be prefixed by dot-separated namespaces.
    Bindings in the environment can be added and retrieved using dict-like syntax, except
    attempting to overwrite an existing binding causes a ``Collision`` error. It's possible for an
    environment to include an empty namespace (containing no actual bindings).
    """

    _items: Dict[str, T]
    _namespaces: Set[str]

    def __init__(self, bindings: Optional[Dict[str, T]] = None):
        self._items = {}
        self._namespaces = set()
        if bindings:
            for k in bindings:
                self[k] = bindings[k]

    def __contains__(self, key: str) -> bool:
        return key in self._items

    def __getitem__(self, key: str) -> T:
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        yield from self._items

    def __setitem__(self, key: str, value: T) -> None:
        assert not key.endswith(".")
        if key in self._items or key in self._namespaces:
            raise Collision(key)
        try:
            pos = key.rindex(".")
            assert pos > 0 and pos < len(key) - 1
            namespace = key[:pos]
            self.add_namespace(namespace, exist_ok=True)
        except ValueError:
            pass
        self._items[key] = value

    def bind(self, key: str, value: T) -> "Base[T]":
        """
        Copy the environment with an additional binding (leaving ``self`` unchanged)
        """
        ans = Base(self._items)
        ans._namespaces = set(self._namespaces)
        ans[key] = value
        return ans

    def add_namespace(self, namespace: str, exist_ok: bool = False) -> None:
        """
        Add a namespace to the environment. When a binding with a namespaced key is added to the
        environment, its namespace is also added automatically. Using this method, it's also
        possible to add an empty namespace (without any bindings).
        
        When a nested namespace is added its parents are also implicitly added, so adding the
        namespace ``foo.bar.`` also adds namespace ``foo.``.
        """
        if namespace.endswith("."):
            namespace = namespace[:-1]
        assert namespace
        if namespace in self:
            raise Collision(namespace)
        if not exist_ok and namespace in self._namespaces:
            raise Collision(namespace)
        try:
            pos = namespace.rindex(".")
            assert pos > 0 and pos < len(namespace) - 1
            self.add_namespace(namespace[:pos], exist_ok=True)
        except ValueError:
            pass
        self._namespaces.add(namespace)

    def contains_namespace(self, namespace: str) -> bool:
        """
        Answer whether the namespace exists in the environment, irrespective of whether it's
        nonempty.
        """
        if namespace.endswith("."):
            namespace = namespace[:-1]
        return namespace in self._namespaces

    def enter_namespace(self, namespace: str) -> "Base[T]":
        """
        Produces the environment obtained by entering the specified namespace. For example if the
        environment has bindings for "fruit.banana" and "fruit.apple.green", then
         ``enter_namespace("fruits")`` produces an environment with bindings for "banana" and
         "apple.green". The namespace must exist in the environment.
        """
        if not self.contains_namespace(namespace):
            raise KeyError(namespace)
        if not namespace.endswith("."):
            namespace = namespace + "."
        ans = Base()
        for k in self:
            if k.startswith(namespace):
                ans[k[len(namespace) :]] = self[k]
        for ns in self._namespaces:
            # add any empty sub-namespaces
            if ns.startswith(namespace):
                ans._namespaces.add(ns[len(namespace) :])
        return ans

    def map(self, fn: Callable[[str, T], S]) -> "Base[S]":
        """
        Copy the environment with the value in each binding replaced by ``fn(key, self[key])``.
        """
        ans = Base()
        for k in self:
            ans[k] = fn(k, self[k])
        ans._namespaces = set(self._namespaces)
        return ans

    def filter(
        self, pred: Callable[[str, T], bool], keep_empty_namespaces: bool = True
    ) -> "Base[T]":
        """
        Copy the environment with only those bindings for which ``pred(key, self[key])`` is truthy.
        """
        ans = Base()
        for k, v in self._items.items():
            if pred(k, v):
                ans[k] = v
        if keep_empty_namespaces:
            ans._namespaces = set(self._namespaces)
        return ans

    def merge(self, rhs: "Base[T]", disjoint_namespaces: bool = True) -> "Base[T]":
        """
        Make a new environment containing the union of bindings.

        :param disjoint_namespaces: if False then the two input environments may share common
        namespaces, so long as their bound keys are all distinct.
        """
        if disjoint_namespaces:
            common = self._namespaces.intersection(rhs._namespaces)
            if common:
                raise Collision(next(iter(common)))
        ans = Base()
        for k in self:
            ans[k] = self[k]
        for k in rhs:
            ans[k] = rhs[k]
        ans._namespaces = self._namespaces.union(rhs._namespaces)
        return ans


class Collision(RuntimeError):
    pass


IntEnv = Base[int]


def _test():
    int_env: Base[int] = IntEnv()
    int_env["foo.bar"] = 42
    str_env: Base[str] = int_env.map(lambda k, v: str(v))
    assert str_env["foo.bar"] == "42"
    k: int = str_env["foo.bar"]
