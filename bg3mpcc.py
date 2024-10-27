from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import ClassVar, Literal

import pandas as pd


class BG3ConflictChecker:
    """Checks for conflicting mods setup by vortex by analysing the `startup.json` file."""

    _folder_with_json_files: Path = Path().cwd() / "data" / "settings_json"
    _folder_with_cleaned_files: Path = Path().cwd() / "data" / "settings_cleaned"
    _json_filepaths: ClassVar[list[Path]] = list(_folder_with_json_files.glob("**/*.json"))
    _folder_with_json_files.mkdir(parents=True, exist_ok=True)
    _folder_with_cleaned_files.mkdir(parents=True, exist_ok=True)
    _dataframe: pd.DataFrame = pd.DataFrame()
    _filtered_dataframe: pd.DataFrame = pd.DataFrame()

    def __init__(self, hosts_file: str | None = None) -> None:
        self._hosts_file = hosts_file.strip(".json") if hosts_file else None
        self.idiot_checker()
        try:
            self.tabulate_json_files()
            self.duplicate_checker()
            self._jcleaned_filepaths: list[Path] = list(
                self._folder_with_cleaned_files.glob("**/*.json"),
            )
            self.conflict_filter()
        except Exception:
            log.exception(
                exit=True,
            )

    def idiot_checker(self) -> None:
        """Checks for comm-HERP DERP DERP!!!- mistakes."""
        if not self._json_filepaths:
            log.exception(
                error_hint="Is the data folder empty?",
                expected_folderpath=self._folder_with_json_files.absolute(),
                exit=True,
            )
        if len(self._json_filepaths) == 1:
            log.exception(
                error_hint="o.O? You need at least 2 files to compare.",
                files_found=self._json_filepaths,
                exit=True,
            )

    def duplicate_checker(self) -> bool:
        """Check if any of the files listed in self._json_filepaths contain the same data. If they do, warn the user."""
        content_hash_to_files = defaultdict(list)

        for filepath in self._json_filepaths:
            filepath: Path
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)
            json_str = json.dumps(
                json.loads(json.dumps(data, sort_keys=True)),
                sort_keys=True,
                separators=(",", ":"),
            )
            content_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
            content_hash_to_files[content_hash].append(filepath)

        d = {k: [file.name for file in v] for k, v in content_hash_to_files.items() if len(v) > 1}
        if not d:
            pass
        else:
            log.exception(
                "Duplicate files found",
                error_hint=f"You have probably duplicated the following: {json.dumps(d, indent=2)}",
                exit=True,
            )

    def tabulate_json_files(self) -> pd.DataFrame:
        """Puts all relavent json data into a dataframe."""
        for startup_file in self._folder_with_json_files.glob("**/*.json"):
            filename = startup_file.name.split(".")[0]
            tmp = self.get_data(file_path=startup_file).sort_values(by="fileMD5")
            tmp["player"] = filename
            tmp.to_json(
                self._folder_with_cleaned_files / f"{filename}.json",
                orient="records",
                indent=2,
            )
            self._dataframe = pd.concat([self._dataframe, tmp], axis=0)

    def conflict_filter(self) -> pd.DataFrame:
        """Filter out all non-conflicting mods."""
        self._filtered_dataframe = pd.DataFrame()
        pivot_table = self._dataframe.pivot_table(
            index="fileMD5",
            columns="player",
            aggfunc="size",
            fill_value=0,
        )
        non_matching_fileMD5s = pivot_table[(pivot_table != 1).any(axis=1)].index
        self._filtered_dataframe = self._dataframe[
            self._dataframe["fileMD5"].isin(non_matching_fileMD5s)
        ]

    def get_data(self, file_path: str) -> pd.DataFrame:
        """Perform ETL on a single `startup.json` file."""
        tmp = pd.DataFrame(pd.read_json(file_path, orient="index").mods.iloc[1])
        tmp = tmp.reset_index().rename(columns={"index": "modname"})

        baldursgate_expanded = tmp.pop("baldursgate3").apply(pd.Series)
        tmp = pd.concat([tmp, baldursgate_expanded], axis=1)

        all_keys = list({key for attr_dict in tmp["attributes"] for key in attr_dict})

        def extract_row_data(row: dict | None) -> dict:
            if isinstance(row, dict):
                return {key: row.get(key, None) for key in all_keys}
            return {"attribute_data": row}

        rows_data = tmp["attributes"].apply(extract_row_data).tolist()
        rows_data_df = pd.DataFrame(rows_data, columns=all_keys)

        tmp = pd.concat([tmp.drop(columns=["attributes"]), rows_data_df], axis=1)
        tmp = tmp[
            [
                "modName",
                "fileName",
                "fileSize",
                "fileMD5",
                "modVersion",
                "modId",
                "state",
                "homepage",
                "downloadGame",
                "customFileName",
                "version",
                "type",
                "isPrimary",
            ]
        ]

        return tmp.dropna(how="all")

    def save_all_conflicts(
        self,
        filetype: Literal["html", "xlsx", "csv"] = "xlsx",
    ) -> None:
        """Save a report showing all conflicts between each players `startup.json` file."""
        tmp = pd.DataFrame()
        for e, url in enumerate(self._filtered_dataframe["homepage"]):
            row_data = self._dataframe[self._dataframe.homepage == url].copy()
            issue_number = f"Issue {e}"
            row_data.loc[:, "issue"] = issue_number
            tmp = pd.concat([tmp, row_data], axis=0)
        output: pd.DataFrame = tmp[
            [
                "fileName",
                "fileMD5",
                "modVersion",  # for some ungodly reason there are 2 version fields, where occaisionally they don't match?? lol@nexus
                "version",  # for some ungodly reason there are 2 version fields, where occaisionally they don't match?? lol@nexus
                "homepage",
                "issue",
                "player",
                "customFileName",  # Another example of duplicated fields
                "modName",  # Another example of duplicated fields
            ]
        ].set_index(
            [
                "issue",
                "player",
                "fileName",
                "fileMD5",
            ],
        )
        filename = f"conflicts.{filetype}"
        if filetype == "html":
            output.to_html(filename)
        elif filetype == "xlsx":
            output.to_excel(filename, engine="openpyxl")
        elif filetype == "csv":
            output.to_csv(filename)
        log.info("Saved conflicts to: %s ", Path.cwd() / filename-)


if __name__ == "__main__":
    from src.logs.handler import configure_logging

    log = configure_logging(
        level="DEBUG",
        log_types=["dev"],
    )
    checker = BG3ConflictChecker(
        hosts_file="player1.json",
    )
    # excel looks neater as it can handle multi-indexed dataframes
    checker.save_all_conflicts()

    # # there are also csv and html options whatever is easier
    # checker.save_all_conflicts("csv")
    # checker.save_all_conflicts("html")
