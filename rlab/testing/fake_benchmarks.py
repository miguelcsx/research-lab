from typing import Protocol


class _Encoder(Protocol):
    def encode(self, text: str) -> list[int]: ...


def count_tokens(target: _Encoder) -> dict[str, float]:
    return {"tokens": float(len(target.encode("test")))}
