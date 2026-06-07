from collections import Counter
from typing import Any


class ConstantBaseline:
    def __init__(self, value: Any = 0) -> None:
        self.value = value

    def __call__(self, _: Any) -> Any:
        return self.value


class MajorityBaseline:
    def __init__(self, labels: tuple[Any, ...]) -> None:
        if not labels:
            raise ValueError("Majority baseline requires labels")
        self.value = Counter(labels).most_common(1)[0][0]

    def __call__(self, _: Any) -> Any:
        return self.value
