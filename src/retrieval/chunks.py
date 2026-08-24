"""Chunk the extracted PDF text into retrievable passages with authority metadata.

Each chunk carries its source's tier/status and (for contracts) the bound
account_id, so the index can gate deprecated docs and scope contract passages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.config import EXTRACTED
from src.domain.sources import SOURCES, Source

_PAGE = re.compile(r"^--- PAGE (\d+) ---$")
_SECTION = re.compile(r"^\d+\.\s")  # numbered section header
_MAX_CHARS = 600


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source_file: str
    page: int
    tier: int
    status: str
    account_id: str | None
    default_retrieval: bool


def _flush(buf: list[str], src: Source, page: int, idx: int) -> Chunk | None:
    text = "\n".join(buf).strip()
    if not text:
        return None
    return Chunk(
        chunk_id=f"{src.filename}#p{page}#{idx}",
        text=text,
        source_file=src.filename,
        page=page,
        tier=int(src.tier),
        status=src.status,
        account_id=src.account_id,
        default_retrieval=src.default_retrieval,
    )


def chunks_for(src: Source) -> list[Chunk]:
    txt = (EXTRACTED / f"{src.filename[:-4]}.txt").read_text(encoding="utf-8")
    out: list[Chunk] = []
    page = 1
    idx = 0
    buf: list[str] = []

    def emit() -> None:
        nonlocal idx, buf
        chunk = _flush(buf, src, page, idx)
        if chunk:
            out.append(chunk)
            idx += 1
        buf = []

    for line in txt.splitlines():
        m = _PAGE.match(line.strip())
        if m:
            emit()
            page = int(m.group(1))
            continue
        # Start a fresh chunk at a new numbered section or when too large.
        if buf and (_SECTION.match(line) or sum(len(x) for x in buf) > _MAX_CHARS):
            emit()
        buf.append(line)
    emit()
    return out


def all_chunks() -> list[Chunk]:
    out: list[Chunk] = []
    for src in SOURCES.values():
        if src.filename.endswith(".pdf"):
            out.extend(chunks_for(src))
    return out
