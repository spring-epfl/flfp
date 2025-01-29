from csv import reader, DictWriter, writer
import os
from pathlib import Path
from typing import Callable, List


class CSVExperimentLogger:

    def __init__(
        self,
        file_path: Path,
        header: List[str],
        mkdir: bool = False,
        append: bool = False,
        delimiter: str = ",",
        id_column: int = 0,
    ):

        self.file_path = file_path
        self.header = header
        self.mkdir = mkdir
        self.append = append
        self.delimiter = delimiter
        self.id_column = id_column
        self.writer = None
        self.file = None
        self._processed_ids = None

    @property
    def processed_ids(self, additional_row_filter: Callable[[list], bool] = None):

        if self._processed_ids is None:
            if not self.file_path.exists():
                self._processed_ids = set()

            if additional_row_filter is None:
                additional_row_filter = lambda x: True

            with open(self.file_path, "r") as f:
                csv = reader(f, delimiter=self.delimiter)

                self._processed_ids = set()

                for i, row in enumerate(csv):

                    if i == 0:
                        # header
                        continue

                    if additional_row_filter(row):
                        self._processed_ids.add(row[self.id_column])

        return self._processed_ids

    def __enter__(self):

        if self.mkdir:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

        if (
            not self.file_path.exists()
            or os.path.getsize(self.file_path) == 0
            or not self.append
        ):
            self.file = open(self.file_path, "w+")
            self.writer = DictWriter(
                self.file, fieldnames=self.header, delimiter=self.delimiter
            )
            self.writer.writeheader()

        else:
            self.file = open(self.file_path, "a+")
            self.writer = DictWriter(
                self.file, fieldnames=self.header, delimiter=self.delimiter
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        self.file = None
        self.writer = None

    def log(self, row: dict):

        if self.writer is None:
            raise ValueError(
                "The writer is not initialized. Did you forget to use the 'with' statement?"
            )

        if not set(row.keys()) == set(self.header):
            raise ValueError(
                f"The row keys {set(row.keys())} do not match the header {set(self.header)}"
            )

        if row[self.header[self.id_column]] in self.processed_ids:
            return

        self.writer.writerow(row)
        self._processed_ids.add(row[self.header[self.id_column]])

        # save to disk
        self.file.flush()
        os.fsync(self.file.fileno())

    def log_many(self, rows: List[dict]):
        for row in rows:
            self.log(row)

    def processed(self, id: str):
        return id in self.processed_ids
