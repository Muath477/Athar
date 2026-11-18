import json
import os
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Any, Self

CHUNK_BYTES = 1024 * 1024


class TrainingArchive:
    def __init__(self) -> None:
        handle, name = tempfile.mkstemp(prefix="athar-training-", suffix=".zip")
        os.close(handle)
        self.path = Path(name)
        self._zip = zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_STORED)
        self._manifest: list[str] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None
    ) -> None:
        self._zip.close()
        if error is not None:
            self.path.unlink(missing_ok=True)

    def add_example(self, image_name: str, jpeg: bytes, record: dict[str, Any]) -> None:
        self._zip.writestr(image_name, jpeg)
        self._manifest.append(json.dumps(record, ensure_ascii=False, sort_keys=True))

    def add_card(self, card: dict[str, Any]) -> None:
        manifest = "".join(f"{line}\n" for line in self._manifest)
        self._zip.writestr("manifest.jsonl", manifest)
        self._zip.writestr("export.json", json.dumps(card, ensure_ascii=False, indent=2))


def stream_and_remove(path: Path) -> Iterator[bytes]:
    try:
        with path.open("rb") as file:
            while chunk := file.read(CHUNK_BYTES):
                yield chunk
    finally:
        path.unlink(missing_ok=True)
