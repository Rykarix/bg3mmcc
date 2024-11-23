from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import ClassVar

import pandas as pd


class BG3ConflictChecker:
    """Checks for conflicting mods setup by vortex by analysing the `startup.json` file."""

    _folder_with_json_files: Path = Path().cwd() / "data" / "settings_json"
    _json_filepaths: ClassVar[list[Path]] = list(_folder_with_json_files.glob("**/*.json"))
    _folder_with_json_files.mkdir(parents=True, exist_ok=True)
    _dataframe: pd.DataFrame = pd.DataFrame()
    _filtered_dataframe: pd.DataFrame = pd.DataFrame()

    def __init__(self, hosts_file: str | None = None) -> None:
        self._hosts_file = hosts_file.strip(".json") if hosts_file else None
        self.idiot_checker()
        try:
            self.tabulate_json_files()
            self.duplicate_checker()
            self.conflict_filter()
        except Exception:
            log.exception(
                exit=True,
            )

    def idiot_checker(self) -> None:
        """Checks for mi-HERP DERP DERP!!!- stakes."""
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
        ].sort_values(by="customFileName")

    def get_data(self, file_path: str) -> pd.DataFrame:
        """Perform ETL on a single `startup.json` file."""
        filename = Path(file_path).name
        tmp = pd.DataFrame(pd.read_json(file_path, orient="index").mods.iloc[1])
        tmp = tmp.reset_index().rename(columns={"index": "modname"})

        baldursgate_expanded = tmp.pop("baldursgate3").apply(pd.Series)
        tmp = pd.concat([tmp, baldursgate_expanded], axis=1)

        # NOTE: A player reported a bug where, for whatever reason, vortex was returning data for mods containing no data in "attributes".
        # Additionally, it appeared to have remembered this fragmented data from a previous profile... The following code should warn users if this has happened:
        invalid_entries = [
            (file_name, attr_dict)
            for file_name, attr_dict in zip(tmp["modname"], tmp["attributes"], strict=False)
            if not isinstance(attr_dict, dict)
        ]
        if invalid_entries:
            invalid_modnames = "\n    ".join(
                f'"modname": "{file_name}"' for file_name, _ in invalid_entries
            )
            log.warning(
                "No attribute data for entries in `%s`. Entries:\n    %s",
                filename,
                invalid_modnames,
            )
            log.warning(
                """This shouldn't happen. Nor should it really cause an issue with your game.
Possible reasons for it happening are:
    1 you didn't create a new profile as instructed
    2 vortex has left remnant data from a previous profile (which has been known to happen).
Possible Solutions are:
    1. Try re-creating your vortex mod profile into a new profile (all you need to do is follow the defaults as suggested by the mod creator).
    2. Try a clean install of vortex. This shouldn't cause too much trouble, since your mods will already be downloaded however you will have to follow the vortex setup guide again.""",
            )

        tmp = tmp.dropna(subset=["attributes"])

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
    ) -> None:
        """Save a report showing all conflicts between each players `startup.json` file."""
        host_filename = self._hosts_file
        host_dataframe = self._dataframe[self._dataframe["player"] == host_filename]
        host_list = host_dataframe[host_dataframe["state"] == "installed"]["homepage"].tolist()
        cols2rem = [
            "player",
            "fileSize",
            "fileMD5",
            "state",
            "downloadGame",
            "type",
            "isPrimary",
            "modId",
        ]
        conflict_folder = Path.cwd() / "data" / "conflict_analysis"
        conflict_folder.mkdir(parents=True, exist_ok=True)
        for player in self._dataframe["player"].unique().tolist():
            if player == host_filename:
                continue
            conflict_dataframe: pd.DataFrame = self._dataframe[self._dataframe["player"] == player]
            conflict_list: list = conflict_dataframe[conflict_dataframe["state"] == "installed"][
                "homepage"
            ].tolist()
            # compare the two lists and find the differences
            diff = list(set(conflict_list) - set(host_list))
            conflict_df = (
                conflict_dataframe[conflict_dataframe["homepage"].isin(diff)]
                .drop(
                    columns=cols2rem,
                )
                .dropna()
                .reset_index(drop=True)
                .sort_values(by="customFileName")
                .set_index("customFileName")
            )

            # if self._INVALID_ENTRIES_FOUND:

            if not conflict_df.empty:
                log.warning(
                    "Found %s conflicting mods between the host: '%s' and player: '%s' ",
                    conflict_df.shape[0],
                    host_filename,
                    player,
                )
                filename = conflict_folder / f"conflicts_{player}.csv"
                conflict_df.to_csv(filename, header=True)
                log.info(
                    "File conflicts have been saved to: %s ",
                    (Path.cwd() / filename).relative_to(Path.cwd()),
                )
            else:
                log.info(
                    "No conflicts found between the host: '%s' and player: '%s' ",
                    host_filename,
                    player,
                )


if __name__ == "__main__":
    import argparse

    from src.logs.handler import configure_logging

    log = configure_logging(level="DEBUG", log_types=["dev"])

    parser = argparse.ArgumentParser(description="BG3 Conflict Checker")
    parser.add_argument(
        "--hosts_file",
        type=str,
        required=True,
        help="Name of the host's state backups JSON file",
    )
    args = parser.parse_args()

    checker = BG3ConflictChecker(hosts_file=args.hosts_file)
    checker.save_all_conflicts()
