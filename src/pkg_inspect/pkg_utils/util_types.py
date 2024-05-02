"""
This module provides various utility types used in the `pipinspect` package.

The types defined in this module are used to enhance type hinting and improve code readability.
They include generic type variables, type aliases, and type unions that are commonly used throughout the project.
"""
from __future__ import annotations

from .utils import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    Path,
    datetime,
    os,
    package_version,
)
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
    Iterator,
    Literal,
    MappingView,
    Match,
    NamedTuple,
    NoReturn,
    Optional,
    Pattern,
    Type,
    Union,
    overload,
)

# Type Hint Variables
CallableT = Callable[..., Any]
ExceptionT = Type[Exception]
PathOrStr = Union[Path, str]
IntOrFloatOrStr = Union[int, float, str]
IntOrFloat = Union[int, float]
OStatResult = os.stat_result
DatesOrVersions = Literal["dates", "versions"]
PyPIOptionsT = Literal[
    "initial_version", "latest_version", "total_versions", "version_history"
]
PackageVersion = Type[package_version.Version]
DateTimeAndVersion = tuple[Union[datetime, PackageVersion]]
TupleOfPkgVersions = tuple[package_version.Version, ...]
MinOrMax = Literal["min", "max"]
TupleDoubleStr = tuple[str, str]
IterablePath = Iterable[Path]
IterablePathOrStr = Iterable[PathOrStr]
TupleExceptions = tuple[ExceptionT]
ExceptionOrTupleExceptions = Union[ExceptionT, TupleExceptions]
OperatorMethods = Literal["eq", "ge", "gt", "le", "lt", "ne"]
IteratorOrIterators = Union[Iterator, Iterator[Iterator]]
ZeroOrOne = Literal[0, 1]
