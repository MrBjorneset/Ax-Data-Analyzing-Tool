# backup.py — classify a complete service backup into the files each tool needs.
# No Streamlit imports: takes raw uploaded objects/bytes in, returns sorted lists.

import io
import zipfile


def _is_csv(name: str) -> bool:
    return name.lower().endswith((".csv", ".tsv"))


def _is_xml(name: str) -> bool:
    return name.lower().endswith(".xml")


def _is_zip(name: str) -> bool:
    return name.lower().endswith(".zip")


def _basename(name: str) -> str:
    # zip entries keep their internal folder path — keep only the file name
    return name.replace("\\", "/").split("/")[-1]


def _expand_zip(data: bytes, csvs: list, xmls: list) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                base = _basename(info.filename)
                if _is_csv(base):
                    csvs.append((base, z.read(info)))
                elif _is_xml(base):
                    xmls.append((base, z.read(info)))
    except zipfile.BadZipFile:
        pass


def classify(uploaded_files) -> tuple[list, list]:
    """
    Sort uploaded files into (csvs, xmls).

    uploaded_files : list of Streamlit UploadedFile objects. .zip files are
                     expanded; their CSV/XML contents are pulled out.

    Returns two lists of (filename, raw_bytes) tuples. De-duplicated by name
    (last one wins) so re-adding a file doesn't create duplicates.
    """
    csvs: list = []
    xmls: list = []

    for f in uploaded_files:
        name = f.name
        data = f.getvalue()  # getvalue() doesn't move the read pointer
        if _is_zip(name):
            _expand_zip(data, csvs, xmls)
        elif _is_csv(name):
            csvs.append((_basename(name), data))
        elif _is_xml(name):
            xmls.append((_basename(name), data))

    return _dedup(csvs), _dedup(xmls)


def _dedup(items: list) -> list:
    seen = {}
    for name, data in items:
        seen[name] = data
    return list(seen.items())