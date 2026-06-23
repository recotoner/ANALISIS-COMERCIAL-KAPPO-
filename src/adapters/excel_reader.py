from pathlib import Path
from typing import BinaryIO

import pandas as pd


ExcelSource = str | Path | BinaryIO


def get_excel_files(project_root: Path) -> list[Path]:
    patterns = ("*.xlsx", "*.xls")
    files: list[Path] = []

    for pattern in patterns:
        files.extend(project_root.glob(pattern))

    return sorted(
        path
        for path in files
        if path.is_file() and not path.name.startswith("~$")
    )


def get_sheet_names(source: ExcelSource) -> list[str]:
    excel_file = pd.ExcelFile(source)
    return excel_file.sheet_names


def read_excel_sheet(source: ExcelSource, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(source, sheet_name=sheet_name)
