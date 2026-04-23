from __future__ import annotations

import zipfile
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    source = root / "ClientSource"
    out_dir = root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / "CareerMPPartySharedVehicles.zip"

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in source.rglob("*"):
            if file_path.is_dir():
                continue
            zf.write(file_path, file_path.relative_to(source).as_posix())

    print(out_zip)
    print(out_zip.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
