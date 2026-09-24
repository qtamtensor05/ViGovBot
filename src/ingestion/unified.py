from __future__ import annotations
import zipfile
from contextlib import contextmanager
from pathlib import Path
from src.utils.helpers import stat_identity

def zip_member(archive, basename):
    # Chỉ đọc đúng file cần thiết; không giải nén đường dẫn do ZIP cung cấp.
    matches = [m for m in archive.infolist()
               if not m.is_dir() and Path(m.filename.replace("\\", "/")).name == basename
               and not m.filename.startswith("__MACOSX/")]
    if len(matches) != 1:
        raise ValueError(f"ZIP cần đúng một {basename}, tìm thấy {len(matches)}")
    return matches[0]


@contextmanager
def corpus_stream(source, basename):
    source = Path(source)
    if source.is_dir():
        with (source / basename).open("rb") as handle:
            yield handle
    else:
        with zipfile.ZipFile(source) as archive:
            with archive.open(zip_member(archive, basename)) as handle:
                yield handle


def corpus_identity(source):
    source = Path(source)
    names = ("tthc_unified.index", "tthc_unified_metadata.json")
    if source.is_dir():
        return {name: stat_identity(source / name) for name in names}
    with zipfile.ZipFile(source) as archive:
        return {"zip": stat_identity(source), "members": {
            name: {"name": m.filename, "crc": m.CRC, "size": m.file_size}
            for name in names for m in [zip_member(archive, name)]}}
