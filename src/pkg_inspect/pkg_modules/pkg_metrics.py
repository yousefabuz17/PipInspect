import shutil

from .pkg_versions import _DateTime
from ..pkg_utils.exception import PkgException
from ..pkg_utils.utils import *

os_exception_handler = partial(
    exception_handler, item="OS Stats", exceptions=(OSError, OverflowError)
)


# region PkgMetrics
class PkgMetrics(Iterable):
    """
    The PkgMetrics class is designed to collect and export OS statistics for specified paths.

    #### Args:
        - `paths` (Iterable): Paths for which to gather statistics.

    ### Kwargs:
        - `full_posix` (bool): Indicates whether to display full POSIX paths.
        - `max_workers` (int): Number of workers for parallel execution.

    #### Methods:
        - `export_stats()`: Export gathered statistics to a JSON file.
        - `all_stats` (property): Get all gathered statistics as a dictionary.
        - `total_size` (property): Retrieve the total size of all specified paths.
        - `total_files` (property): Retrieves the total number of specified paths.
    """

    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_paths",
        "_full_posix",
        "_workers",
        "_all_stats",
    )

    def __init__(
        self,
        paths: IterablePathOrStr = None,
        *,
        full_posix: bool = False,
        max_workers: int = None,
    ) -> None:
        # Parameters
        self._workers = max_workers
        self._full_posix = full_posix
        self._paths = self._validate_paths(paths)

        # Attributes
        self._all_stats = None

    def __iter__(self) -> Iterator[tuple[str, namedtuple]]:
        """Returns an iterator for the dataset statistics."""
        return iter(self.all_metric_stats.items())

    def __len__(self) -> int:
        """Returns the number of validated files in the dataset."""
        return len(self.all_metric_stats)

    def __sizeof__(self) -> int:
        """
        Calculate the size or number of files in the dataset.

        #### Returns:
            - `int`: Total size of files in bytes if size is True. Number of files in the dataset if files is True.

        #### Notes:
            - If both size and files are False, the method returns None.
            - The size of a file is determined by the bytes_size attribute in the dataset statistics.
        """

        total_bytes = sum(
            j.bytes_size for _k, v in self for i, j in v.items() if i == "st_fsize"
        )
        return bytes_converter(total_bytes)

    def _validate_paths(self, paths: IterablePathOrStr) -> IterablePath:
        """
        Validates and returns the specified paths.

        #### Args:
            - `paths` IterablePathOrStr: Paths to be validated.

        #### Returns:
            - `IterablePath`: Validated paths.
        """
        if not paths:
            return
        return executor(validate_file, paths, max_workers=self._workers)

    def _get_stats(self) -> dict[str, dict[str, NamedTuple]]:
        return {
            get_package_name(p.name)
            if not self._full_posix
            else p.as_posix(): self._os_stats(p)
            for p in self._paths
        }

    @classmethod
    def convert_timestamp(cls, dt_timestamp: float, as_dt: bool = False) -> NamedTuple:
        """
        Converts a timestamp to a human-readable format.

        #### Args:
            - `dt_timestamp` (float): The timestamp to convert.

        #### Returns:
            - `NamedTuple`: A NamedTuple containing the timestamp in human-readable format.

        #### Example:
            ```python
            dt = PkgMetrics.convert_timestamp(1631536800)
            print(dt)
            # Output: DateTime(seconds=1631536800, date='Jan 1, 0001', time='12:00:00 AM')
            ```
        """

        @os_exception_handler(
            item=f"the 'datetime' timestamp conversion for {dt_timestamp}"
        )
        def dt_convert(t):
            return _DateTime(seconds=t, with_time=True).dt_seconds

        return subclass(date=True, *dt_convert(dt_timestamp))

    @os_exception_handler()
    def _path_stats(self, path: PathOrStr, stats_results: bool = False) -> OStatResult:
        default_stats = os.stat(path)
        if stats_results:
            default_stats = os.stat_result(default_stats)
        return default_stats

    @os_exception_handler()
    def _os_stats(
        self, path: PathOrStr = None, keys_only: bool = False
    ) -> dict[str, IntOrFloat]:
        if not path:
            path = DUMMY_FILE
        stats_results = self._path_stats(path, stats_results=True)
        metric_keys = set(k for k in dir(stats_results) if k.startswith("st"))

        if keys_only:
            for s in ("st_fsize", "st_vsize"):
                metric_keys.add(s)
            return metric_keys

        disk_usage = shutil.disk_usage(path)._asdict()

        def gattr(a):
            return getattr(stats_results, a, None)

        hattr = partial(hasattr, stats_results)

        def birth_time() -> float:
            # Using 'st_birthtime' if available, else 'st_ctime'
            birth_time = ct_time = gattr("st_ctime")
            if all(
                (
                    hattr("st_birthtime"),
                    hattr("st_ctime"),
                )
            ):
                birth_time = next(filter(bool, (gattr("st_birthtime"), ct_time)))
            return self.convert_timestamp(birth_time)

        # Convert bytes size to human-readable format
        # Retrieve stats that:
        #   1. is not empty (None)
        #   2. prefix == "st" (stat) | postfix == "size"
        os_stats = {
            **{
                attr: bytes_converter(gattr(attr))
                # Convert byte size to human-readable format
                if attr.endswith("size")
                # Get the real birthtime (creation time) value depending on OS.
                else birth_time() if attr in ("st_birthtime", "st_ctime")
                # Convert the datetime value to human-readable format if the attribute ends with "time"
                else self.convert_timestamp(gattr(attr), as_dt=True)
                if attr.endswith("time")
                # Otherwise, retrieve the standard result value if it is not None
                else gattr(attr)
                for attr in metric_keys
                # Filter values that is not None
                if gattr(attr) is not None
            },
            # Custom stats for 'st_size' and 'volume'
            **{
                # 'fsize' -> Full size
                "st_fsize": subclass(
                    bstats=True,
                    *bytes_converter(stats_results.st_size, symbol_only=True),
                ),
                # 'v_size' -> Volume Stats
                "st_vsize": {k: bytes_converter(v) for k, v in disk_usage.items()},
            },
        }

        return os_stats

    def export_stats(self, file_name: str = "pipmetrics_stats") -> None:
        """
        Exports gathered statistics to a JSON file.

        #### Args:
            - `file_name` (str): Name of the file to export statistics.

        #### Example:
            ```python
            pm = PkgMetrics(paths=[file:=j[1] for i,j in PipInspect(False).package_paths])
            pm.export_stats(file_name="testing")
            ```

        """
        exporter(file_name, self.all_metric_stats, suffix="json")

    @cached_property
    def get_metrickeys(self) -> set[str]:
        return self._os_stats(keys_only=True)

    def date_installed(self, package: str, date_only: bool = True) -> Union[str, None]:
        """
        Retrieves the installation date of a specified package.
        
        #### Args:
            - `package` (str): The package for which to retrieve the installation date.
        
        #### Returns:
            - `DateTime` (NamedTuple[str, _DateTime, str]): \
                The installation date of the specified package.
                Example: `DateTime(seconds=1631536800, date='Jan 1, 0001', time='12:00:00 AM')`
                Note: The date is an instance of the `_DateTime` class.
                    - `seconds` (property): Seconds since the epoch.
                    - `date` (property): The parsed version of the date.
                    - `time` (property): The time in human-readable format.
        """

        # Ensure that the package argument is a string
        if not isinstance(package, str):
            raise PkgException(
                "The package argument must be a string containing the package name."
                "Please ensure that the package name is an installed package and is within the specified paths."
            )

        # Retrieve the installation date of the specified package
        all_stats = self.all_metric_stats
        date_installed = next(
            (
                all_stats[pkg].get("st_birthtime", all_stats[pkg]["st_ctime"])
                for pkg in all_stats
                if get_package_name(pkg) == package
            ),
            None,
        )

        if date_installed is None:
            raise PkgException(
                f"The specified package ({package!r}) installation date could not be found."
            )

        if date_only:
            # Return the date only
            return date_installed.date
        # Return the full DateTime NamedTuple
        return date_installed

    @property
    def all_metric_stats(self) -> dict[str, dict[str, IntOrFloatOrStr]]:
        """
        Retrieves all gathered statistics as a dictionary.

        #### Returns:
            - `dict` (dict[str, dict[str, Union[int, float, str]]]): \
                All gathered statistics as a dictionary.
        """
        if self._all_stats is None:
            self._all_stats = self._get_stats()
        return self._all_stats

    @property
    def total_size(self) -> int:
        """
        Retrieves the total size of all specified paths in a `NamedTuple` with human-readable format.

        #### Returns:
            - `NamedTuple`: A NamedTuple containing the total stats of all specified paths with human-readable format.
        """
        return self.__sizeof__()


# endregion
