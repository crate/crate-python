import typing as t
from functools import cached_property


class BulkResultItem(t.TypedDict):
    """
    Define the shape of a CrateDB bulk request response item.
    """

    rowcount: int


class BulkResponse:
    """
    Manage a response to a CrateDB bulk request.
    Accepts a list of bulk arguments (parameter list) and a list of bulk response items.

    https://cratedb.com/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
    """

    def __init__(
            self,
            records: t.List[t.Dict[str, t.Any]],
            results: t.List[BulkResultItem]):
        if records is None:
            raise ValueError("Processing a bulk response without records is an invalid operation")
        if results is None:
            raise ValueError("Processing a bulk response without results is an invalid operation")
        self.records = records
        self.results = results

    @cached_property
    def failed_records(self) -> t.List[t.Dict[str, t.Any]]:
        """
        Compute list of failed records.

        CrateDB signals failed inserts using `rowcount=-2`.

        https://cratedb.com/docs/crate/reference/en/latest/interfaces/http.html#error-handling
        """
        errors: t.List[t.Dict[str, t.Any]] = []
        for record, status in zip(self.records, self.results):
            if status["rowcount"] == -2:
                errors.append(record)
        return errors

    @cached_property
    def record_count(self) -> int:
        """
        Compute bulk size / length of parameter list.
        """
        if not self.records:
            return 0
        return len(self.records)

    @cached_property
    def success_count(self) -> int:
        """
        Compute number of succeeding records within a batch.
        """
        return self.record_count - self.failed_count

    @cached_property
    def failed_count(self) -> int:
        """
        Compute number of failed records within a batch.
        """
        return len(self.failed_records)
