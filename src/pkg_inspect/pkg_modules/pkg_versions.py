from __future__ import annotations

import importlib_metadata
from bs4 import BeautifulSoup

from ..pkg_utils.utils import *
from ..pkg_utils.exception import PkgException, RedPkgE


# region _DateTime
class _DateTime(Iterable):
    """
    This class provides the ability to parse and store a specified string date or seconds as a `datetime` instance.

    ### Args:
        - `seconds` (int, optional): The seconds to parse. Defaults to None.
        - `date` (str, optional): The date to parse. Defaults to None.
        - `with_time` (bool, optional): Whether to include the time in the date. Defaults to False.

    ### Attributes:
        - `MIN_DATE` (str): The minimum date value.
        - `DATE_ONLY` (str): The date format without the time.
        - `DATE_W_TIME` (str): The date format with the time.

    ### Properties:
        - `dt_date`: property containing the parsed date.
        - `dt_seconds`: property containing the parsed seconds.

    ### Example:
    ```python
    # In this example, a `_DateTime` instance is created with the specified date and seconds.
    dt_instance = _DateTime(date="Jan 1, 2021", with_time=True)
    print(dt_instance.dt_date)
    # Output: datetime.datetime(2021, 1, 1, 0, 0)

    dt_instance = _DateTime(seconds=1609459200)
    print(dt_instance.dt_seconds)
    # Output: (1609459200, 'Jan 1, 2021', '00:00:00')
    ```

    """

    # The minimum date value
    MIN_DATE: str = "Jan 1, 0001"
    # The date format without the time
    DATE_ONLY: str = "%b %d, %Y"
    # The date format with the time
    DATE_W_TIME: str = DATE_ONLY + "T%I:%M:%S %p"

    __dict__ = {}
    __slots__ = ("__weakrefs", "_date", "_seconds", "_wt")

    def __init__(
        self, seconds: IntOrFloat = None, date: str = None, with_time: bool = False
    ) -> None:
        self._date = date
        self._seconds = seconds
        self._wt = with_time

    def __iter__(self) -> Iterator:
        return iter(filter(None, (self.dt_date, self.dt_seconds)))

    def __getitem__(self, num: int) -> Any:
        try:
            return (*self,)[num]
        except IndexError as idxe:
            raise idxe

    def __hash__(self) -> int:
        return hash((*self,))

    def __len__(self) -> int:
        return len(Counter(self))

    @staticmethod
    def _splitime(dt_) -> Union[datetime, list[str]]:
        if isinstance(dt_, datetime):
            return dt_
        return dt_.split("T")

    @classmethod
    def _strftime(cls, dt_, dt_format: str = None) -> str:
        dtf = dt_format or cls.DATE_W_TIME
        return datetime.strftime(dt_, dtf)

    @classmethod
    def _strptime(cls, dt_, dt_format: str = None) -> datetime:
        dtf = dt_format or cls.DATE_ONLY
        return datetime.strptime(dt_, dtf)

    @classmethod
    def _parse_seconds(cls, seconds: IntOrFloat) -> NamedTuple:
        if seconds:
            dt_date = datetime.fromtimestamp(seconds)
            dt_stamp = cls._strftime(dt_date)
            datetime_, time_ = cls._splitime(dt_stamp)
            return subclass(seconds, datetime_, time_, date=True)

    @classmethod
    def _parse_date(
        cls,
        __dt: str,
        method: Literal["strftime", "strptime"] = "strptime",
        with_time: bool = False,
    ) -> datetime:
        """Parse the specified date using the `datetime` module."""
        if isinstance(__dt, datetime) and method == "strptime":
            return __dt

        wt = (cls.DATE_ONLY, cls.DATE_W_TIME)[with_time]
        try:
            if method == "strftime":
                dt_stamp = cls._strftime(__dt, wt)
            elif method == "strptime":
                dt_stamp = cls._strptime(__dt, wt)
        except ValueError:
            return cls._strptime(__dt, cls.DATE_ONLY)
        return dt_stamp

    @property
    def dt_date(self) -> datetime:
        return self._parse_date(self._date, with_time=self._wt)

    @property
    def dt_seconds(self) -> NamedTuple:
        return self._parse_seconds(self._seconds)


# endregion


# region _DTVersions
class _DateTimeVersions(_DateTime):
    """
    This class provides the ability to parse and store the release date and version of a package.
    The release date and version are parsed and stored as a `datetime` instance and a `version.Version` instance, respectively.

    ### Args:
        - `date` (str, optional): The release date of the package. Defaults to an empty string.
            - Note: The default release date is set to "Jan 1, 0001".
        - `version` (str, optional): The version of the package. Defaults to an empty string.
            - Note: The default version is set to "0.0.0".

    ### Attributes:
        - `date`: Cached property containing the parsed release date of the package.
        - `version`: Cached property containing the parsed version of the package.
        - `distribution`: Cached property containing the release date and version of the package.

    ### Methods:
        - `__iter__`: Return an iterator of the release date and version.
        - `__getitem__`: Return the specified item from the release date and version.
        - `__str__`: Return the string representation of the `_DateTimeVersions` instance.
        - `__format__`: Return the string representation of the specified format.
        - `operator_handler`: Decorator to handle comparison operators for the `_DateTimeVersions` class.
        - `__gt__`: Compare the specified object with the current `_DateTimeVersions` instance.
        - `__lt__`: Compare the specified object with the current `_DateTimeVersions` instance.
        - `__eq__`: Compare the specified object with the current `_DateTimeVersions` instance.
        - `__ne__`: Compare the specified object with the current `_DateTimeVersions` instance.
        - `__ge__`: Compare the specified object with the current `_DateTimeVersions` instance.
        - `__le__`: Compare the specified object with the current `_DateTimeVersions` instance.

    ### Example:
    ```python
    # In this example, a `_DateTimeVersions` instance is created with the specified release date and version.
    dtv_instance = _DateTimeVersions("Jan 1, 2021", "2.25.1")
    print(dtv_instance.date)
    # Output: datetime.datetime(2021, 1, 1, 0, 0)
    print(dtv_instance.version)
    # Output: <Version('2.25.1')>
    print(dtv_instance.distribution)
    # Output: ('Jan 1, 2021', '2.25.1')

    # Compare the release date and version of the specified `_DateTimeVersions` instances.
    print(_DateTimeVersions("Jan 1, 2021", "2.25.1") < _DateTimeVersions("Jan 2, 2021", "2.25.1"))
    # Output: True
    print(_DateTimeVersions("Jan 1, 2021", "2.25.1") > _DateTimeVersions("Jan 2, 2021", "2.25.1"))
    # Output: False
    print(_DateTimeVersions("Jan 1, 2021", "2.25.1") == _DateTimeVersions("Jan 1, 2021", "2.25.1"))
    # Output: True
    print(_DateTimeVersions("Jan 1, 2021") != _DateTimeVersions("Jan 1, 2021", "2.25.1"))
    # Output: False
    print(_DateTimeVersions("Jan 1, 2021", "2.25.1") >= _DateTimeVersions("Jan 1, 2021", "2.25.1"))
    # Output: True
    print(_DateTimeVersions("2.25.1") < _DateTimeVersions("Jan 1, 2021", "2.25.1"))
    # Output: True (Date is not specified, default is Jan 1, 1969)
    """

    MIN_VERSION: str = "0.0.0"

    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "__datet",
        "__pipv",
        "_d",
        "_v",
    )

    def __init__(
        self,
        date: str = "Jan 1, 0001",
        version: str = "0.0.0",
        with_time: bool = False,
    ) -> None:
        self._d = self._validate_dtv(date)
        self._v = self._validate_dtv(version, is_version=True)
        self._wt = with_time

        # `PkgVersions` is not inherited to avoid possible circular imports
        self.__pipv = PkgVersions
        self.__datet = self.__class__.__base__

    def __iter__(self) -> Iterator[DateTimeAndVersion]:
        return iter((self.date, self.version))

    def __getitem__(self, num: int) -> DateTimeAndVersion:
        try:
            # self: (date, version)
            return (*self,)[num]
        except IndexError as idxe:
            raise idxe

    def __hash__(self) -> int:
        return super().__hash__()

    def __str__(self) -> str:
        """
        Return the string representation of the `_DateTimeVersions` instance.

        - If both the release date and version are present, the string representation will be in the format: \n
        `('release_date', 'version')`.
            - Example: `('Jan 1, 2021', '2.25.1')`
            - Formats:
                - `release_date` (`datetime` instance)
                    - `strftime`: Jan 1, 2021 (string representation)
                    - `strptime`: 2021-01-01 00:00:00 (string representation)
                - `version` (`version.Version` instance)
                    - `base_version`: 2.25.1 (string representation)
                    - `parsed_version`: <Version('2.25.1')> (string representation)
        """

        valid_date = self.__pipv.compare_dates(self.date, self.MIN_DATE, "ne")
        valid_version = self.__pipv.compare_versions(
            self.base_version, self.MIN_VERSION, "ne"
        )

        if all((valid_date, valid_version)):
            return f"{(self.__format__('dt'), self.__format__('vn'))}"

        if valid_date:
            return self.__format__("dt")
        elif valid_version:
            return self.__format__("vn")
        return self.__class__.__name__ + "()"

    __repr__ = __str__

    def __format__(self, format_spec: str) -> str:
        """
        Return the string representation of the specified format.

        ### Args:
            - `format_spec` (str): The format to use for the string representation.
                - Options:
                    - `dt` (date): Return the string representation of the release date.
                    - `vn` (version): Return the string representation of the version.

        ### Returns:
            - `str`: The string representation of the specified format.
        """
        if format_spec == "dt":
            # dt -> date
            return self._parse_date(self.date, method="strftime")
        elif format_spec == "vn":
            # vn -> version
            return self.base_version

        # Raise a `PkgException` if the specified format is not valid
        raise PkgException(
            f"The specified 'format_spec' is not a valid option: {format_spec!r}"
        )

    def operator_handler(op_method: OperatorMethods, version_only: bool = False):
        """
        This decorator is used to handle comparison operators for the `_DateTimeVersions` class.

        ### Args:
            - `op_method` (OperatorMethods): The operator method to use for comparison.
                - Options: ('==', '>=', '>', '<=', '<', '!=', 'eq', 'ge', 'gt', 'le', 'lt', 'ne')

        ### Returns:
            - `Callable`: The decorator function.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.

        ### Notes:
            - If the release dates are equal, the versions are compared.
            - If the release dates are not equal, the release dates are compared.
        """

        def decorator(func):
            @wraps(func)
            def wrapper(self, __other: Union[_DateTimeVersions, Any]):
                # E.g 'operator.lt', 'operator.eq', ...
                op: operator[Any] = get_opmethod(op_method)

                if version_only:
                    v1, v2 = func(self, __other)
                    if "__pipv" in self.__slots__:
                        vparser = self.__pipv.parse_version
                    else:
                        vparser = self.parse_version
                    return op(v1.version, vparser(v2))

                if all(
                    map(lambda x: not isinstance(x, _DateTimeVersions), (self, __other))
                ):
                    # Raise a `PkgException` if the specified object is not an instance of `_DateTimeVersions`.
                    raise PkgException(
                        "The specified objects must be an instance of '_DateTimeVersions'."
                        "\nInvalid types:"
                        f"\n{type(self) = }"
                        f"\n{type(__other) = }"
                    )

                # E.g 'operator.lt', 'operator.eq', ...
                # op: operator[Any] = get_opmethod(op_method)
                if all(self) and all(__other):
                    # Compare the release dates and versions
                    # If the release dates are equal, compare the versions
                    return (
                        op(self.date, __other.date),
                        op(self.version, __other.version),
                    )[self.date == __other.date]

                if all((self.date, __other.date)):
                    # Compare the release dates only
                    return op(self.date, __other.date)

                if all((self.version, __other.version)):
                    # Compare the versions only
                    return op(self.version, __other.version)

            return wrapper

        return decorator

    @operator_handler(">")
    def __gt__(self, __other: _DateTimeVersions) -> bool:
        """
        Compare the specified object with the current `_DateTimeVersions` instance.

        This method compares the current `_DateTimeVersions` object with another `_DateTimeVersions` object,
        evaluating their release dates and versions. If both objects have valid release dates, it
        first compares the release dates. If the release dates are equal, it then compares the versions.

        ### Args:
            - `__other` (_DateTimeVersions): The other `_DateTimeVersions` object to compare with the current object with.

        ### Returns:
            - `bool`: True if the current object is greater than the other object, False otherwise.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.
        """
        # (self.date, self.version) > (__other.date, __other.version)
        return self, __other

    @operator_handler("<")
    def __lt__(self, __other: _DateTimeVersions) -> bool:
        """
        Compare the specified object with the current `_DateTimeVersions` instance.

        This method compares the current `_DateTimeVersions` object with another `_DateTimeVersions` object,
        evaluating their release dates and versions. If both objects have valid release dates, it
        first compares the release dates. If the release dates are equal, it then compares the versions.

        ### Args:
            - `__other` (_DateTimeVersions): The other `_DateTimeVersions` object to compare with the current object with.

        ### Returns:
            - `bool`: True if the current object is less than the other object, False otherwise.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.
        """
        # (self.date, self.version) < (__other.date, __other.version)
        return self, __other

    @operator_handler("==")
    def __eq__(self, __other: _DateTimeVersions) -> bool:
        """
        Compare the specified object with the current `_DateTimeVersions` instance.

        This method compares the current `_DateTimeVersions` object with another `_DateTimeVersions` object,
        evaluating their release dates and versions. If both objects have valid release dates, it
        first compares the release dates. If the release dates are equal, it then compares the versions.

        ### Args:
            - `__other` (_DateTimeVersions): The other `_DateTimeVersions` object to compare with the current object with.

        ### Returns:
            - `bool`: True if the current object is equal to the other object, False otherwise.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.
        """
        # (self.date, self.version) == (__other.date, __other.version)
        return self, __other

    @operator_handler("!=")
    def __ne__(self, __other: _DateTimeVersions) -> bool:
        """
        Compare the specified object with the current `_DateTimeVersions` instance.

        This method compares the current `_DateTimeVersions` object with another `_DateTimeVersions` object,
        evaluating their release dates and versions. If both objects have valid release dates, it
        first compares the release dates. If the release dates are equal, it then compares the versions.

        ### Args:
            - `__other` (_DateTimeVersions): The other `_DateTimeVersions` object to compare with the current object with.

        ### Returns:
            - `bool`: True if the current object is not equal to the other object, False otherwise.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.
        """
        # (self.date, self.version) != (__other.date, __other.version)
        return self, __other

    @operator_handler(">=")
    def __ge__(self, __other: _DateTimeVersions) -> bool:
        """
        Compare the specified object with the current `_DateTimeVersions` instance.

        This method compares the current `_DateTimeVersions` object with another `_DateTimeVersions` object,
        evaluating their release dates and versions. If both objects have valid release dates, it
        first compares the release dates. If the release dates are equal, it then compares the versions.

        ### Args:
            - `__other` (_DateTimeVersions): The other `_DateTimeVersions` object to compare with the current object with.

        ### Returns:
            - `bool`: True if the current object is greater than or equal to the other object, False otherwise.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.
        """
        # (self.date, self.version) >= (__other.date, __other.version)
        return self, __other

    @operator_handler("<=")
    def __le__(self, __other: _DateTimeVersions) -> bool:
        """
        Compare the specified object with the current `_DateTimeVersions` instance.

        This method compares the current `_DateTimeVersions` object with another `_DateTimeVersions` object,
        evaluating their release dates and versions. If both objects have valid release dates, it
        first compares the release dates. If the release dates are equal, it then compares the versions.

        ### Args:
            - `__other` (_DateTimeVersions): The other `_DateTimeVersions` object to compare with the current object with.

        ### Returns:
            - `bool`: True if the current object is less than or equal to the other object, False otherwise.

        ### Raises:
            - `PkgException`: If the specified object is not an instance of `_DateTimeVersions`.
        """
        # (self.date, self.version) <= (__other.date, __other.version)
        return self, __other

    def _validate_dtv(self, dtv: Any, is_version: bool = False) -> DateTimeAndVersion:
        """
        Validate the specified date or version.

        ### Args:
            - `dtv` (Any): The date or version to validate.

        ### Returns:
            - `Union[datetime, version.Version]`: The parsed date or version.

        ### Notes:
            - The specified date or version is considered invalid if it is not an instance of `datetime`, `version.Version` or `str`.
            - If the specified date or version is None, it will be returned as an empty string.
        """
        if dtv is None:
            # Raise a `PkgException` if the specified date or version is None
            raise PkgException(
                "The specified 'date' and 'version' arguments cannot be None."
            )

        if not isinstance(dtv, (datetime, package_version.Version, IntOrFloatOrStr)):
            # Raise a `PkgException` if the specified date or version is not a valid instance
            raise PkgException(
                "The specified 'date' and 'version' arguments are considered invalid."
                "\nValid options: ('datetime', 'version.Version', 'str')"
                f"\nInvalid: ({dtv!r})"
            )

        # If the specified date or version is an empty string, return the minimum date or version
        if dtv == "":
            if is_version:
                # Return the minimum version
                return self.MIN_VERSION
            # Return the minimum date
            return self.MIN_DATE
        # Return the specified date or version
        return dtv

    @property
    def date(self) -> datetime:
        """Return the parsed release date of the package."""
        return self.__datet(date=self._d, with_time=self._wt).dt_date

    @property
    def version(self) -> PackageVersion:
        """Return the parsed version of the package."""
        return self.__pipv.parse_version(self._v)

    @property
    def base_version(self) -> str:
        """Return the base version of the package."""
        return self.version.base_version

    @property
    def distribution(self) -> tuple[datetime, PackageVersion]:
        """
        Retrieve a tuple containing the parsed release date and version of the specified package.

        The release date is represented as a `datetime` object, while the version is represented as a `version.Version` object.

        ### Returns:
            - `tuple[datetime, version.Version]`: The parsed release date and version of the package.

        ### Example:
        ```python
        # Example usage to retrieve the release date and version of the package.
        dtv = _DateTimeVersions("Jan 1, 2021", "2.25.1")
        print(dtv.distribution)
        # Output:
        # ('Jan 01, 2021', '2.25.1')
        # Formats:
        (datetime.datetime(2021, 1, 1, 0, 0), <Version('2.25.1')>)
        ```
        """
        return self

    @property
    def default_distributions(self) -> tuple[datetime, PackageVersion]:
        return self._parse_date(self.MIN_DATE), self.__pipv.parse_version(
            self.MIN_VERSION
        )


# endregion


class _DtvRepr(Iterable):
    __slots__ = (
        "__weakrefs__",
        "__dtv",
    )

    def __init__(self, __dtv) -> None:
        self.__dtv = (_DateTimeVersions(*i) for i in __dtv)

    def __iter__(self) -> Iterator:
        return iter(self.__dtv)

    def __getitem__(self, num: int) -> DateTimeAndVersion:
        try:
            return (*self,)[num]
        except IndexError as idxe:
            raise idxe

    def __str__(self):
        return f"{*self,}"

    def __repr__(self) -> str:
        return PkgGenRepr(self).__repr__()


# region PkgVersions
class PkgVersions:
    """
    This class provides the ability to fetch and parse the version history of a specified package from `PyPI`.
    It includes methods for fetching the version history and parsing the release dates of the package versions.

    ### Args:
        - `package` (str): The name of the package for which to fetch the version history.
        - `package_manager` (str, optional): The package manager to use for fetching GitHub statistics.
        - `sort_by` (Union[DatesOrVersions, ZeroOrOne], optional): The sorting method to use for the version history.
            - Options:
                - `dates`: Sort the version history by the release dates.
                - `versions`: Sort the version history by the package versions.
                - `0`: Do not sort the version history.
                - `1`: Sort the version history by the package versions.
                - `reverse`: Reverse the sorting order.
            - Defaults to 'versions'.
        - `generator` (bool, optional): Whether to return the version history as a generator. Defaults to True.

    ### Attributes:
        - `API` (str): The API endpoint for fetching package versions.
        - `DATE_PATTERN` (Pattern): Pattern for matching release dates.

    ### Methods:
        - `version_history`: Property containing the version history of the specified package.
        - `initial_version`: Property containing the initial version of the package.
        - `latest_version`: Property containing the latest version of the package.
        - `is_latest`: Property to check if the specified version is the latest version.
        - `total_versions`: Property containing the total number of versions in the version history.
        - `get_updates`: Method to retrieve the available updates for the specified package.

    ### Example:
    ```python
    version_instance = PkgVersions("pandas")
    print(version_instance.version_history)
    # Output: (('2.25.1', 'Jan 1, 2021'), ('2.25.0', 'Dec 1, 2020'), ...)
    ```
    """

    # The API endpoint for fetching package versions
    PYPI_API: str = "https://pypi.org/project/{}/#history"
    STATS_API: str = "https://libraries.io/{}/{}"

    # Pattern for matching release dates
    # Example: "Jan 1, 2021"
    # This pattern is specifically designed for the `PkgVersions` class to accurately match release dates
    # when parsing package version history release dates from PyPI.
    DATE_PATTERN: Pattern = r"[A-Z][a-z]{2}\s\d{1,2},\s\d{4}"

    # Pattern for matching package versions
    # - The pattern matches the version number in the format 'x.x' or 'x.x.x'.
    # - The pattern is used to extract the version number from any of the following:
    #       1. the package METADATA file.
    #       2. the package version history page (if available from the package's PyPI page).
    # Examples:
    #       1. "1.5"
    #       2. "4.25.1"
    VERSION_PATTERN: Pattern = r"\d+\.\d+(\.\d+)?"

    # TODO: Implement beta versions
    BETA_VERSION_PATTERN: Pattern = r"(beta|dev|pre[-_ ]?release|rc)"

    # The minimum version number
    # This value is used to set the minimum version number when parsing version strings.
    MIN_VERSION: str = _DateTimeVersions.MIN_VERSION

    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_pkg_name",
        "_pkg_manager",
        "_pkg_url",
        "_pkg_path",
        "_sort_by",
        "_generator",
        "_vhistory",
        "_initial",
        "_latest",
        "_gh_stats",
    )

    def __init__(
        self,
        package: str,
        package_manager: str = None,
        *,
        sort_by: Union[DatesOrVersions, ZeroOrOne] = "versions",
        generator=True,
    ) -> None:
        # Example: `PkgVersions("pandas") < PkgVersions("pandas")`
        # Compares the latest version of the specified package with the latest version of the other package

        # Parameters
        self._pkg_name = package
        self._pkg_manager = package_manager
        self._pkg_path = self._validate_package(self._pkg_name)
        self._pkg_url = self._pkg_path.removesuffix("#history")
        self._sort_by = sort_by
        self._generator = generator

        # Properties
        self._vhistory = None  # Version History
        self._initial = None  # Initial Version
        self._latest = None  # Latest Version
        self._gh_stats = None

    def __len__(self) -> int:
        """Return the total number of versions in the version history."""
        return len((*self._version_history(),))

    def __sizeof__(self) -> int:
        """Return the total number of versions in the version history."""
        return len(self)

    def __iter__(self) -> Generator[Any, Any, None]:
        """Return an iterator of the version history."""
        return iter(self._version_history())

    def __getitem__(self, num: int) -> TupleDoubleStr:
        """Return the specified item from the version history."""
        try:
            return (*self,)[num]
        except IndexError as idxe:
            raise idxe

    def __hash__(self) -> int:
        """Return the hash value of the version history."""
        return hash(self.version_history)

    @classmethod
    def import_version(
        cls, package_name: str, parse_version: bool = False
    ) -> Union[PackageVersion, str]:
        """
        Retrieve the version of the specified package using the `importlib.metadata` module.

        ### Args:
            - `package_name` (str): The name of the package to retrieve the version.
            - `parse_version` (bool, optional): Whether to parse the version using the `packaging.version` module. Defaults to False.

        ### Returns:
            - `Union[version.Version, str]`: The version of the specified package.
        """
        try:
            # Retrieve the version of the specified package
            found_ver = importlib_metadata.version(package_name)
        except (*BASE_EXCEPTIONS, importlib_metadata.PackageNotFoundError):
            # If the package is not found, return the minimum version
            found_ver = cls.MIN_VERSION
        return cls.parse_version(found_ver) if parse_version else found_ver

    def _validate_generator(self, gen: Generator) -> Generator:
        if not is_generator(gen):
            # Return the object if it is not a generator or iterator
            return gen

        gens = clone_gen(gen, iter_only=True)
        # Check if the generator yields tuples of ('datetime', 'package_version.Version')
        if not next(
            (
                all(
                    (
                        isinstance(d, datetime),
                        isinstance(v, package_version.Version),
                    )
                )
                for d, v in next(gens)
            ),
            False,
        ):
            raise RedPkgE(
                "The specified generator must contain valid 'datetime' and 'version.Version' instances."
            )

        yield from next(gens)

    @staticmethod
    def create_dtv(*args, **kwargs) -> _DateTimeVersions:
        """
        Create a `_DateTimeVersions` instance with the specified release date and version.

        ### Note:
            - Use `create_dtv.__doc__` to view the `_DateTimeVersions` class documentation.
        """
        PkgVersions.create_dtv.__doc__ = (
            PkgVersions.create_dtv.__doc__ + _DateTimeVersions.__doc__
        )
        return _DateTimeVersions(*args, **kwargs)

    @staticmethod
    def create_datetime(*args, **kwargs) -> _DateTime:
        """
        Create a `_DateTime` instance with the specified date and seconds.

        ### Note:
            - Use `create_datetime.__doc__` to view the `_DateTime` class documentation.
        """
        PkgVersions.create_datetime.__doc__ = (
            PkgVersions.create_datetime.__doc__ + _DateTime.__doc__
        )
        return _DateTime(*args, **kwargs)

    def _validate_package(
        self, pkg: str, api: str = None, package_manager: str = None
    ) -> str:
        """Validate the specified package is not None and is a valid string value."""
        if any((not pkg, not isinstance(pkg, str))):
            raise RedPkgE(
                "The specified package must be a valid string value.",
                f"\nInvalid: ({pkg!r})",
            )
        if not api:
            api = self.PYPI_API

        format_api = api.format

        if api == self.STATS_API:
            pm = best_match(package_manager, PACKAGE_MANAGERS)
            if not pm:
                pm = "pypi"
            return format_api(pm.lower(), pkg)

        return format_api(pkg)

    @staticmethod
    def parse_version(
        version: str = None, return_base: bool = False
    ) -> Union[PackageVersion, str]:
        """
        Parse the specified version using the `packaging.version` module.

        ### Args:
            - `version` (str): The version to parse.
            Note: If None, returns "0.0.0" (base version) or <Version('0.0.0')> (parsed version)
            - `return_base` (bool, optional): Whether to return the base version (str). Defaults to True.
                - Example:
                    - "2.25.1" (base version) or <Version('0.1')> (parsed version)

        ### Notes:
            - The `return_base` argument is used to specify whether to return the base version (str) or the parsed version (version.Version).
            - If the `version` argument is already an instance of `version.Version`, the `return_base` argument is ignored.

        ### Returns:
            - `Union[version.Version, str]`: The parsed version.
        """

        if isinstance(version, package_version.Version):
            # If the version is already parsed, return the parsed version or the base version.
            return version

        try:
            # Parse the version using the `packaging.version` module
            if version is None:
                version = PkgVersions.MIN_VERSION
            parsed_version: PackageVersion = package_version.parse(version)
            return [parsed_version, getattr(parsed_version, "base_version")][
                return_base
            ]
        except (*BASE_EXCEPTIONS, package_version.InvalidVersion):
            raise RedPkgE(
                f"The specified {version = } is not a valid version format to parse."
            )

    @classmethod
    def _compare_items(
        cls,
        items: Iterable[TupleDoubleStr],
        op_method: str,
        item_type: DatesOrVersions,
    ) -> bool:
        # Ensure that the specified item type is valid
        if item_type not in ("dates", "versions"):
            raise RedPkgE(
                f"The specified operator method {item_type!r} is not a valid option."
            )

        @exception_handler(
            item=f"the differences in the specified {item_type!r}.\nInvalid: ({items, op_method, item_type!r})",
            exceptions=AttributeError,
        )
        def compare(items_, op):
            # Get the operator method to use for comparison
            op = get_opmethod(op)

            # Retrieve the attr to use for comparison
            # E.g `date` or `version`
            attr = item_type.rstrip("s")

            # Parse the date or version using the `_DateTimeVersions` class
            # Compare the items using the specified operator method
            return op(*(cls.create_dtv(**{attr: i}) for i in items_))

        # Return the result of the comparison
        return compare(items, op_method)

    @classmethod
    def compare_versions(
        cls, current_vh: str, other_vh: str, op_method: str = "gt"
    ) -> bool:
        """
        Compare two versions using the specified operator method.

        ### Args:
            - `current_vh` (str): The current version to compare.
            - `other_vh` (str): The other version to compare.
            - `op_method` (str, optional): The operator method to use for comparison. Defaults to "lt".

        ### Returns:
            - `bool`: The result of the comparison.

        ### Raises:
            - `AttributeError`: If the specified operator method is not valid.
            - `PkgException`: If the specified operator method is not valid.
        """
        return cls._compare_items(
            items=(current_vh, other_vh), op_method=op_method, item_type="versions"
        )

    @classmethod
    def compare_dates(
        cls, current_dt: str, other_dt: str, op_method: str = "gt"
    ) -> bool:
        """
        Compare two dates using the specified operator method.

        ### Args:
            - `current_dt` (str): The current date to compare.
            - `other_dt` (str): The other date to compare.
            - `op_method` (str, optional): The operator method to use for comparison. Defaults to "lt".

        ### Returns:
            - `bool`: The result of the comparison.

        ### Raises:
            - `AttributeError`: If the specified operator method is not valid.
            - `PkgException`: If the specified operator method is not valid.
        """
        return cls._compare_items(
            items=(current_dt, other_dt), op_method=op_method, item_type="dates"
        )

    @cache
    def _main_request(self, url: PathOrStr) -> Union[str, Any]:
        """Return the main asynchronous request for the version history page (#history) of the specified package."""
        try:
            return asyncio.run(url_request(url))
        except ClientResponseError:
            raise RedPkgE(
                f"An error occurred while trying to find {url!r}.",
                "Please ensure the package name and manager is correct and is available on the following websites:"
                f"\n- {self.package_url = }"
                f"\n- {self.github_stats_url = }",
            )
        except BASE_EXCEPTIONS as be_error:
            raise be_error

    def _parse_html(self, html_contents: str) -> BeautifulSoup:
        return BeautifulSoup(html_contents, "html.parser")

    def _history_page(self) -> Generator[Any, str, None]:
        # Parse the specified package history release page using BeautifulSoup.
        # Return the release distribution.
        hsoup: BeautifulSoup = self._parse_html(self._main_request(self._pkg_path))
        yield from (
            rd  # release-date
            for i in hsoup.find_all("div", class_="release")
            # Removes all instances of pre-releases
            if search(self.VERSION_PATTERN, rd := i.get_text(strip=True))
        )

    def _get_gh_stats(self, keys_only: bool = False):
        gh_soup = self._parse_html(self._main_request(self.github_stats_url))
        stats_chart = [
            _j
            for i in gh_soup.find_all("dl", class_="row detail-card")
            for j in i.text.splitlines()
            if (_j := re.sub(r"\s{2,}", "", j))
        ]
        gh_stats = None
        if stats_chart:
            try:
                first_key = find_best_match(stats_chart, GH_STATS)
                flat_stats = stats_chart[stats_chart.index(first_key) :]
                gh_stats = {
                    # E.g., '7' -> 7
                    k: int(v) if v.isdigit()
                    # E.g., '1,023' -> 1023
                    else int(clean(v)) if search(r"[,][^a-zA-Z]", v)
                    # E.g., '12.4 MB' -> Stats NamedTuple
                    else str_to_bytes(*v.split())
                    if v[0].isdigit() and search(r"(?:KB|MB|GB|TB)", v)
                    else v
                    for k, v in zip(flat_stats[::2], flat_stats[1::2])
                    if best_match(k, GH_STATS)
                }
            except BASE_EXCEPTIONS:
                ...
        
        if all((keys_only, gh_stats)):
            return (*sorted(gh_stats),)
        return gh_stats

    @classmethod
    def gh_stat_keys(cls) -> tuple[str]:
        return cls(package=DUMMY_PKGNAME)._get_gh_stats(keys_only=True) or GH_STATS

    def _version_history(self) -> Generator[DateTimeAndVersion, None, None]:
        @exception_handler(item=f"{self._pkg_path!r}", exceptions=TimeoutError)
        def get_vers(p: Pattern):
            def search_func(i):
                return search(pattern=p, obj=i, compiler=True).group()

            return executor(search_func, self._history_page(), timeout=LONG_TIMEOUT)

        # Tuple containing the release date and version of the package:
        #  - release_date ('datetime' instance)
        #  - version ('version.Version' instance)
        return _DtvRepr(
            self.create_dtv(*dv)
            for dv in zip(
                get_vers(self.DATE_PATTERN),
                get_vers(self.VERSION_PATTERN),
            )
        )

    def _get_dtv(self, method: MinOrMax = max) -> TupleDoubleStr:
        """Return the initial or latest release date and version of the package."""
        return [min, max][method == max](self._version_history(), key=itemgetter(1))

    @property
    def version_history(self) -> Generator[DateTimeAndVersion, Any, None]:
        """Cached property containing the version history of the specified package."""
        if self._vhistory is None:
            self._vhistory = self._version_history()
        return self._vhistory

    @property
    def initial_version(self) -> TupleDoubleStr:
        """Return the initial release date and version of the package."""
        if self._initial is None:
            self._initial = self.create_dtv(*self._get_dtv(method=min))
        return self._initial

    @property
    def latest_version(self) -> TupleDoubleStr:
        """Return the latest release date and version of the package."""
        if self._latest is None:
            self._latest = self.create_dtv(*self._get_dtv(method=max))
        return self._latest

    @property
    def total_versions(self) -> int:
        """Return the total number of versions in the version history."""
        return self.__sizeof__()

    @property
    def github_stats(self):
        if self._gh_stats is None:
            self._gh_stats = self._get_gh_stats()
        return self._gh_stats

    @property
    def package_url(self):
        return self._pkg_url

    @property
    def github_stats_url(self):
        return self._validate_package(
            self._pkg_name, self.STATS_API, package_manager=self._pkg_manager
        )

    @_DateTimeVersions.operator_handler("==", version_only=True)
    def is_latest(self, other_py: PackageVersion) -> bool:
        """Check if the specified version is the latest version."""
        return self.latest_version, self.parse_version(other_py)

    def get_updates(self, current_version: str) -> Optional[Iterator[PackageVersion]]:
        """
        Retrieve the available updates for a package based on the current version.
        
        - If the `current_version` is not provided, the function will \
            attempt to retrieve the current version of the package installed
            on the most recent Python version available on the system.
        
        - If the `current_version` is specified, the function will attempt to \
            retrieve the available updates for the package based on the specified version \
            and the most recent version available on the system.
        
        - If the `include_betas` argument is set to `True`, the function will \
            attempt to retrieve beta (pre-release) packages when checking for updates.
        
        #### NOTE: Beta (pre-release) packages are currently not supported yet \
            and will be ignored when checking for updates.
        """
        current_v = self.parse_version(current_version)
        version_h = sorted(v for _, v in self._version_history())
        # TODO: Implement beta versions
        # beta_h = sorted(v for _, v in self._pre_releases())
        # full_history = version_h + beta_h

        try:
            # Get the index of the current version in the version history
            current_v_idx = version_h.index(current_v)
        except ValueError:
            # Raise a `PkgException` if the current version is not found in the version history
            raise PkgException(
                f"Appears {current_v!r} was not found in {self._pkg_name!r} versions history."
            )
        # Get the updates after the current version
        updates = version_h[current_v_idx + 1 :]
        if not updates or self.is_latest(current_v):
            updates = None
            # Print a warning message if no updates are found
            # or if the specified version is the latest version.
            print(
                f"\033[1;33mNo updates were found. The specified version ({current_v!r}) appears to be the latest.\033[0m"
            )
        return updates


# endregion
