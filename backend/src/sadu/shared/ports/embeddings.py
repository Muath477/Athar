from typing import Protocol


class EmbeddingPort(Protocol):
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
