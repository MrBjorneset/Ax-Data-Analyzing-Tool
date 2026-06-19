# backup.py — classify a Domino service backup into the files each tool needs.
# No Streamlit imports: takes raw uploaded objects/bytes in, returns sorted lists.
#
# FOLDER RULES (Domino Ax backup layout)
# --------------------------------------
#   storageCard2/
#     Config/                         -> XML machine settings   (Settings Inventory)
#       ...subfolders...              -> also included
#     Labels/                         -> ignored
#     Scripts/                        -> ignored
#     Diagnostics/
#       Datacollection/
#         Uberlogs/                   -> CSV logs               (Log Analyzer)
#         Uberlogs_slow/              -> CSV logs               (Log Analyzer)
#       (everything else)             -> ignored
#     Databases/                      -> ignored
#
# These rules apply to files inside a .zip (zip entries keep their folder path).
# Loose individually-uploaded files have no folder path — they're accepted by
# extension as a best-effort fallback.

import io
import zipfile

CONFIG_DIR = "config"                       # XML wanted if this dir is in the path
UBERLOG_DIRS = {"uberlogs", "uberlogs_slow"}  # CSV wanted if one of these is in the path


def _is_csv(name: str) -> bool:
    return name.lower().endswith((".csv", ".tsv"))


def _is_xml(name: str) -> bool:
    return name.lower().endswith(".xml")


def _is_zip(name: str) -> bool:
    return name.lower().endswith(".zip")


def _segments(path: str) -> list[str]:
    return [s for s in path.replace("\\", "/").split("/") if s]


def _basename(path: str) -> str:
    return path.replace("\\", "/").split("/")[-1]


def _has_path(name: str) -> bool:
    return "/" in name or "\\" in name


def _xml_wanted(path: str) -> bool:
    return any(s.lower() == CONFIG_DIR for s in _segments(path))


def _csv_wanted(path: str) -> bool:
    return any(s.lower() in UBERLOG_DIRS for s in _segments(path))


def _expand_zip(data: bytes, csvs: list, xmls: list) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                path = info.filename
                base = _basename(path)
                if _is_csv(base) and _csv_wanted(path):
                    csvs.append((base, z.read(info)))
                elif _is_xml(base) and _xml_wanted(path):
                    xmls.append((base, z.read(info)))
    except zipfile.BadZipFile:
        pass


def classify(uploaded_files) -> tuple[list, list]:
    """
    Sort uploaded files into (csvs, xmls), applying the Domino backup folder
    rules to anything that carries a folder path (zip contents, or loose files
    whose name happens to include a path).

    Returns two lists of (filename, raw_bytes) tuples, de-duplicated by name.
    """
    csvs: list = []
    xmls: list = []

    for f in uploaded_files:
        name = f.name
        data = f.getvalue()  # getvalue() doesn't move the read pointer

        if _is_zip(name):
            _expand_zip(data, csvs, xmls)

        elif _is_csv(name):
            if not _has_path(name) or _csv_wanted(name):
                csvs.append((_basename(name), data))

        elif _is_xml(name):
            if not _has_path(name) or _xml_wanted(name):
                xmls.append((_basename(name), data))

    return _dedup(csvs), _dedup(xmls)


def _dedup(items: list) -> list:
    seen = {}
    for name, data in items:
        seen[name] = data
    return list(seen.items())