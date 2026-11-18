import csv
import io
from collections.abc import Iterable, Sequence

from fastapi.responses import Response

UTF8_BOM = "﻿"
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

type Cell = str | int | float | None


def csv_bytes(header: Sequence[str], rows: Iterable[Sequence[Cell]]) -> bytes:
    buffer = io.StringIO()
    buffer.write(UTF8_BOM)
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows([_safe(cell) for cell in row] for row in rows)
    return buffer.getvalue().encode("utf-8")


def csv_download(filename: str, header: Sequence[str], rows: Iterable[Sequence[Cell]]) -> Response:
    return Response(
        csv_bytes(header, rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


def _safe(cell: Cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, int | float):
        return str(cell)
    return f"'{cell}" if cell.startswith(FORMULA_PREFIXES) else cell
