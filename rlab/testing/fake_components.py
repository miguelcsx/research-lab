class FakeTokenizer:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text)))

    def decode(self, ids: list[int]) -> str:
        return "x" * len(ids)
