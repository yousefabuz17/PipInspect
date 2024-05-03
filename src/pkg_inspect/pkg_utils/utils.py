"""
This module contains utility functions for the `pkg-inspect` package, \
offering a diverse set of tools for common tasks.
"""
from __future__ import annotations

# Shared Modules
import asyncio
import importlib
import inspect
import json
import operator
import os
import re
from aiohttp import ClientSession, TCPConnector
from aiohttp.client_exceptions import (
    ClientConnectionError,
    ClientResponseError,
    ContentTypeError,
    InvalidURL,
    ServerDisconnectedError,
)
from collections import Counter, namedtuple
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from functools import cache, cached_property, partial, wraps
from itertools import chain, cycle, filterfalse, islice, tee
from operator import itemgetter
from packaging import version as package_version
from pathlib import Path
from random import SystemRandom
from rapidfuzz import fuzz, process
from reprlib import recursive_repr
from string import ascii_letters, ascii_lowercase, ascii_uppercase, digits, punctuation

# Exception Handler and Type Hint Variables
from .exception import PkgException, RedPkgE
from .util_types import *


try:
    import pypistats
except ModuleNotFoundError:
    ...


# MARK: - Constants, Variables, Functions and Exception Handling

# Default 'DUMMY' values to be used for extracting
#   1. package metadata
#   2. Distribution Information
#   3. GitHub Statistics
DUMMY_FILE: Path = Path(__file__)
DUMMY_PKGNAME: str = "requests"


# Field names and custom types to extract
# from the package's METADATA file or dist-info ('site_path') directory.
METADATA_FIELDS: tuple[str] = (
    # - 'METADATA' fieldnames
    "Author",
    "Author-email",
    "Classifier",
    "Description-Content-Type",
    "Download-URL",
    "Home-page",
    "Metadata-Version",
    "Name",
    "Platform",
    "Summary",
    # - 'dist-info' possible file names
    "entry_points",
    "installer",
    "license",
    "metadata",
    "record",
    "requested",
    "top_level",
    "wheel",
)


# Default fields to extract from
# 'libraries.io/<package_manager>/<package>' API
PACKAGE_MANAGERS: tuple[str] = (
    "npm",
    "Maven",
    "PyPI",
    "NuGet",
    "Go",
    "Packagist",
    "Rubygems",
    "Cargo",
    "CocoaPods",
    "Bower",
    "Pub",
    "CPAN",
    "CRAN",
    "Clojars",
    "conda",
    "Hackage",
    "Hex",
    "Meteor",
    "Homebrew",
    "Puppet",
    "Carthage",
    "SwiftPM",
    "Julia",
    "Elm",
    "Dub",
    "Racket",
    "Nimble",
    "Haxelib",
    "PureScript",
    "Alcatraz",
    "Inqlude",
)


GH_STATS: tuple[str] = (
    "Contributors",
    "Dependencies",
    "Dependent packages",
    "Dependent repositories",
    "Forks",
    "Repository size",
    "SourceRank",
    "Stars",
    "Total releases",
    "Watchers",
)


# Exception Handling - Base exceptions to catch
# ---------------------------------------------
# - (Exception, TypeError, ValueError)
BASE_EXCEPTIONS: TupleExceptions = PkgException.BASE_EXCEPTIONS


# Default base for converting bytes to other units
BYTES_BASE: int = 1024


# Default Exception Handlers for Base Exceptions
# --------------------------------------------
exception_handler: CallableT = PkgException.exception_handler
base_exception_handler = partial(exception_handler, exceptions=BASE_EXCEPTIONS)


# Default Timeouts for concurrent execution
# -----------------------------------------
DEFAULT_TIMEOUT: int = 300  # 5 minute
LONG_TIMEOUT: int = 900  # 15 minutes


# region OperatorUtils
def get_opmethod(
    opmethod: OperatorMethods, all_methods: bool = False, *, allow_none: bool = False
) -> Optional[Any]:
    """Check the specified operator method is valid."""
    comparison_ops = {
        "==": "eq",
        ">=": "ge",
        ">": "gt",
        "<=": "le",
        "<": "lt",
        "!=": "ne",
    }
    if not allow_none:
        if not all_methods:
            if opmethod not in chain.from_iterable(zip(*comparison_ops.items())):
                raise PkgException(
                    f"The specified operator method {opmethod!r} is not a valid comparison operator."
                )

        elif all_methods and not hasattr(operator, opmethod):
            raise PkgException(
                f"The specified operator method {opmethod!r} is not a valid option."
            )
    # Return the operator method if valid
    # E.g `operator.gt`, `operator.lt`, `operator.eq`
    return getattr(operator, comparison_ops.get(opmethod, opmethod), None)


# Default operator methods
_gopm = partial(get_opmethod, all_methods=True)
add_ = _gopm("add")
multiply_ = _gopm("mul")
pow_ = _gopm("pow")
equal_ = get_opmethod("eq")
lessthan_ = get_opmethod("lt")


# region InspectUtils
def is_function(c):
    """This function checks if the specified object is a function."""
    return inspect.isfunction(c)


def is_class(c):
    """This function checks if the specified object is a class."""
    return inspect.isclass(c)


def get_members(*args):
    """This function inspects the given object and returns its members."""
    return inspect.getmembers(*args)


def get_parameters(c):
    """This function inspects the given function and returns the names of its parameters."""
    return inspect.signature(c).parameters


def get_sourcefile(c):
    """This function inspects the given object and returns the source file."""
    return inspect.getsourcefile(c)


def has_decorators(c, decorator: str = "__wrapped__"):
    return hasattr(c, decorator)


# endregion


# region ExecutorUtil
def executor(func: Callable, *args: Iterable, **kwargs: Any) -> Iterator[Any]:
    """
    Execute the specified function concurrently using the selected executor pool.
    The function is applied to the specified arguments and keyword arguments
    using the selected executor pool.


    #### Args:
        - `func` (Callable): The function to execute concurrently.
        - `args` (Iterable): The arguments to apply the function to.
        - `kwargs` (Any): The keyword arguments for the function.
            - `epool` (Union[Union[ProcessPoolExecutor, Literal["PPEx"]], Union[ThreadPoolExecutor, Literal["TPEx"]]]): \
                The executor pool to use for the concurrent execution.
                - Defaults to `ThreadPoolExecutor`.
            - Including `<epool.map>` kwargs.
                - `max_workers` (int, optional): The maximum number of workers to use for the concurrent execution.
                - `chunksize` (int, optional): The chunksize to use for the concurrent execution.
                - `timeout` (int, optional): The timeout to use for the concurrent execution.
                    - Defaults to `DEFAULT_TIMEOUT` (300 seconds).

    #### Returns:
        - `Iterator`: The result of the concurrent execution.

    #### Raises:
        - `PipException`: The 'max_workers' argument must be None or a positive integer value.
    """
    # Extract the 'max_workers' and 'epool' arguments from the keyword arguments
    mw, epool, kwargs = popkwargs("max_workers", "epool", **kwargs)

    # Ensure the 'max_workers' argument is a valid type.
    if all((mw is not None, not isinstance(mw, int))):
        raise PkgException(
            "The 'max_workers' argument must be None or a positive integer value."
        )

    # Select the executor pool to use for the concurrent execution
    # - Defaults to 'ThreadPoolExecutor' if not provided.
    _exec = [ThreadPoolExecutor, ProcessPoolExecutor][
        # Can either be the object or the string representation
        epool
        in (ProcessPoolExecutor, "PPEx")
    ]

    # Execute the function concurrently using the selected executor pool
    yield from _exec(max_workers=mw).map(func, *args, **kwargs)


# endregion


# region DuplicateUtils
@cache
def dup_obj(obj: Any, num: int = 2) -> tuple[Any, ...]:
    """
    Return a tuple of values based on the specified number.

    #### Args:
        - `obj` (Any, optional): The object to clone.
        - `num` (int, optional): The number of values to return. Defaults to `2`.

    #### Returns:
        - `tuple`: A tuple of values based on the specified number.

    #### Raises:
        - `PipException`: If the provided number is not a positive integer value.
    """

    @base_exception_handler(msg=f"Failed at returning {num =!r}-{obj!r} values.")
    def dup_obj_(o, n):
        return (o,) * n

    return dup_obj_(obj, num)


def none(num: int) -> tuple[None, ...]:
    """Return a tuple of `None` values based on the specified number."""
    return dup_obj(obj=None, num=num)


# endregion


# region UniqueUtils
def unique_test(__iterable: Iterable[Any]) -> bool:
    """
    This function tests the uniqueness of the elements in the specified iterable
    by checking that each element occurs exactly once in the extracted set.

    #### Args:
        - `__iterable` (Iterable[Any]): The iterable to test for uniqueness.

    #### Returns:
        - `bool`: A boolean value indicating whether the elements are unique.

    #### Raises:
        - `PipException`: An error occurred while testing the uniqueness of the specified iterable.

    #### Example:
    ```python
    unique_test([1, 2, 3, 4, 5, 6, 7, 8, 9, 0])
    # Output: True

    unique_test([1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1])
    # Output: False
    ```
    """

    @base_exception_handler(
        msg=f"Failed at testing the uniqueness of the specified iterable:\n{__iterable!r}"
    )
    def unique_test_(i):
        return all(s == 1 for s in Counter(i).values())

    return unique_test_(__iterable)


def generate_id(
    length: int = 12,
    exclude: Union[Literal["digits", "lower", "upper"], str] = "",
    *,
    ensure_unique: bool = False,
) -> str:
    """
    Generate a (unique) ID sample based on the specified length and excluded characters.
    This function ensures the uniqueness of the generated ID by checking that each character
    occurs exactly once in the extracted set.

    #### Args:
        - `length` (int): The length representing the desired set of characters.
            - Defaults to 12.
        - `exclude` (Union[Literal["digits", "lower", "upper"], str]): The characters to exclude from the generated ID.
            Possible values are: 'digits', 'lower', 'upper', or a custom string of characters.
        - `ensure_unique` (bool, optional): A flag indicating whether to ensure the uniqueness of the generated ID.

    #### Returns:
        - `str`: A unique id sample.

    #### Raises:
        - `PipException`:
            - If the provided group value is outside the valid range of the total length of 'ascii_lowercase' and 'digits'.
            - If the specified characters to exclude are not of type 'str'.
            - If the specified characters to exclude all the characters in the character set.
            - If the specified length is not a positive integer value.
            - If the unique flag is set to True and the length is outside the valid range of the total length of the character set.

    #### Note:
        - The function ensures the uniqueness of the generated id sample by checking that each character
        occurs exactly once in the extracted set.
        - If the condition is not met, the function recursively generates a new sample until a unique one is found.
        - The default characters used for the unique ID are 'ascii_letters' + 'digits'.
        - The maximum length of the unique ID is the total length of 'ascii_letters' and 'digits'
        (i.e., 62 characters).
        - The function also allows for the exclusion of specific characters from the default characters.
        - The length of the characters is also dependent on the excluded characters.

    #### Example:
    ```python
    generate_id()
    # Output: 'ae9cx4g5h6i7'

    generate_id(length=4)
    # Output: 'ae9c3'

    generate_id(length=4, exclude="ae9c3")
    # Output: 'f4g5'
    ```
    """

    err_msg = "The specified length must be a positive integer value and within the character length range: {} = {!r}".format
    # Ensure the length is the correct value type
    if any((not length, not isinstance(length, (float, int)))):
        # If the length is not a positive integer
        raise PkgException(err_msg("\n>>> length", length))
    else:
        # Ensure the length is a positive integer
        length = abs(int(length))

    # Define the characters to use for the unique ID
    # - The default characters ascii_letters + digits
    default_chars = ascii_letters + digits
    if not isinstance(exclude, str):
        # Ensure the characters to exclude are of type 'str'
        raise PkgException("The specified characters to exclude must be of type 'str'.")
    elif exclude == "digits":
        # Exclude digits from the default characters
        exclude = digits
    elif exclude == "lower":
        # Exclude lowercase letters from the default characters
        exclude = ascii_lowercase
    elif exclude == "upper":
        # Exclude uppercase letters from the default characters
        exclude = ascii_uppercase
    # Else, use the specified characters to exclude if provided
    # E.g. exclude = "ae9‰c3"

    # Clean the specified characters to exclude from the default characters
    chars = clean(default_chars, exclude=exclude)
    len_org_chars = len(chars)
    if len_org_chars == 0:
        # If the length of the original characters is zero
        raise PkgException(
            err_msg("\n>>> length of characters (after exclusion)", len_org_chars)
        )
    # Ensure the length is within the valid range for unique characters
    can_be_unique: bool = ensure_unique and 1 <= length <= len_org_chars
    # Max length is either the length of the original characters or 1e3
    max_char_len: int = len_org_chars if can_be_unique else int(1e3)

    if ensure_unique and not can_be_unique:
        # Raise an exception if the unique flag is set to True
        # and the length is outside the valid range of the total length of the character set.
        raise PkgException(
            "It is important to note that the specified length is outside the valid range for unique characters."
            "The specified length must be of value:"
            f"\n>>> 1 <= length <= {len_org_chars!r}"
            "\n>> Please note the length of characters is also dependent on the excluded characters."
        )

    # Create a cycle of the iterable characters
    all_chars = islice(cycle(chars), max_char_len)

    @base_exception_handler(item="Custom (Unique) ID")
    def create_id(l, mk):
        # Generate a random set of characters
        random_set = randset(population=sjoin(all_chars), k=min(l, max_char_len))
        sample_id = unique_sample = sjoin(random_set)

        # Create a set to store the generated IDs
        created_ids = set()
        # Ensure the uniqueness of the generated ID sample
        if can_be_unique:
            # If the unique flag is set to True
            while not unique_test(sample_id) and sample_id not in created_ids:
                # Recursively generate a new sample until a unique one is created.
                unique_sample = create_id(l, mk)

                if unique_sample in created_ids:
                    # If the unique sample has already been created
                    # Recursively generate a new sample until a unique one is created.
                    continue
            # Add the generated (unique) ID to the set
            created_ids._add(unique_sample)
        # Return the generated (unique) ID
        return unique_sample

    # Initialize the recursive function
    return create_id(length, ensure_unique)


# endregion


# region CleanUtils
def clean(s: str, exclude: str = "", keep_punct: bool = False) -> str:
    """
    Remove all instances of a specified character from a string.

    #### Args:
        - `s` (str): The string to clean.
        - `exclude` (str): The character(s) to exclude from the string.
        - `keep_punct` (bool): A flag indicating whether to keep punctuation characters in the string.

    #### Returns:
        - `str`: The cleaned string.

    #### Note:
        - The function removes all instances of the specified character(s) from the string.
        - Punctuation characters are removed by default.

    #### Example:
    ```python
    clean("ae9c3f4g5h6i7j8k9l0", "ae9c3")
    # Output: 'f4g5h6i7j8k9l0'

    clean("ae9c3f4g5h6i7j8k9l0", string.ascii_lowercase)
    # Output: '93657890'
    ```

    """

    @base_exception_handler(item="the specified string.")
    def clean_(s_):
        return s_.translate(
            str.maketrans("", "", add_(exclude, "" if keep_punct else punctuation))
        )

    return clean_(s)


def rm_period(s: str) -> str:
    """Remove all instances of a period from a string."""
    return clean(s, ".", keep_punct=True)


# endregion

# region GenUtils


class PkgGenRepr(Iterable):
    """
    This class is used to represent a generator object and provide a custom string representation.

    ##### Example:
    ```python
    print(PkgGenRepr(range(10)))
    # Output: <PkgGenRepr object as 0x...>
    ```
    """

    __slots__ = ("__weakrefs__", "_gen", "_gen_id")

    def __init__(self, gen) -> None:
        self._gen = gen
        self._gen_id = hex(id(self._gen))

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} object at {self._gen_id}>"

    __repr__ = __str__

    def __iter__(self) -> Iterator:
        return iter(self._gen)

    def __getitem__(self, num: int) -> Any:
        try:
            return (*self,)[num]
        except IndexError as idxe:
            raise idxe


def unpack_generator(data: Any, method: Any = tuple, is_string: bool = False) -> Any:
    """
    Unpacks and transforms the elements of a generator or iterable using a specified method.

    #### Args:
        - `data` (Iterable): A key-value pair generator or iterable to be unpacked.
        - `method` (callable): The method used to transform the elements.

    #### Returns:
        - `Any`: The result of applying the transformation.
    """

    # Duplicate the generator to iterate over it twice
    if is_string:
        try:
            return method(data)
        except:
            return data

    gens = clone_gen(data, n=3, tee_only=True)
    try:

        def transform(
            pair, not_pair: bool = False
        ) -> Union[tuple[Any, Any], tuple[Any, tuple], tuple[Any, str]]:
            excts = BASE_EXCEPTIONS
            # If 'not_pair' is True, apply the method directly to the pair
            if not_pair:
                try:
                    return method(pair)
                except excts:
                    # If an exception occurs during the transformation
                    # return the original pair
                    return pair

            key, value = none(2)
            try:
                key, value = pair
                return key, method(value)
            except excts:
                if not isinstance(value, (int, str)):
                    # If value is not an int or str
                    # transform value into a tuple by default
                    return key, tuple(value)
                return key, value

        # Apply the transform function to each pair in the first duplicate of the generator
        return method(transform(pair) for pair in gens[0])
    except TypeError:
        # If a TypeError occurs
        # it might be due to not having pairs; try again for not paired elements
        return method(transform(pair, not_pair=True) for pair in gens[1])
    except Exception:
        # Return the original data
        return gens[-1]


def generator_handler(other_func: str = "", **other_kwargs):
    """
    This decorator handles the generator object and validates the generator object if specified.

    - Checks if the '_generator' attribute is set to 'False' in the
    instance. If set to 'False', the decorated method's result is unpacked and
    transformed; otherwise, it returns the original generator.
    - If the '_validator' attribute is set in the instance, the decorated method
    is validated using the specified validator function.

    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Union[Any, Generator]:
            f = func(self, *args, **kwargs)

            is_string, mtd, kwgs = popkwargs("is_string", "method", **other_kwargs)
            if not mtd:
                mtd = tuple

            if hasattr(self, "_generator") and not self._generator:
                return unpack_generator(f, method=mtd, is_string=is_string)

            if all(
                (
                    isinstance(other_func, str),
                    hasattr(*(objects_ := (self, other_func))),
                )
            ):
                gen = getattr(*objects_)(f)
            else:
                try:
                    gen = clone_gen(f, **kwgs)
                except:
                    return f
            return PkgGenRepr(gen)

        return wrapper

    return decorator


def is_generator(gen) -> Union[Generator, Literal[False]]:
    """Check if the specified object is a generator or iterator."""
    if isinstance(gen, (Generator, Iterator)):
        return gen
    return False


def clone_gen(
    generator, n: int = 2, tee_only: bool = False, iter_only: bool = False
) -> IteratorOrIterators:
    """
    Clone an generator object.

    #### Args:
        - `generator` (Generator): The generator object to clone.
        - `n` (int): The number of clones to create.
        - `iter_only` (bool): A flag indicating whether to return the iterator only.

    #### Returns:
        - `Generator`: The cloned generator object.
    """

    @base_exception_handler(item="the cloned generator object.")
    def clone_gen_(g, n_) -> Iterator[Iterator]:
        # Validate and convert the generator object to an iterable tee object
        if not is_generator(g):
            g = iter(g)
        return tee(g, n_)

    # Clone the generator object
    gens = clone_gen_(generator, n)
    if all((tee_only, iter_only)):
        # Raise an exception if both 'tee_only' and 'iter_only' are set to True
        raise PkgException(
            "The arguments 'tee_only' and 'iter_only' are mutually exclusive."
        )
    if tee_only:
        # Return the cloned generator objects
        return gens
    elif iter_only:
        # Return the iterator only
        return iter(gens)
    # Otherwise, return the cloned generator object
    return next(iter(gens))


# endregion


# region Wrappers
def sort_distributions(values_only: bool = False, use_itemgetter: bool = True):
    """
    Decorator to sort distributions based on the specified sort type.

    ##### Args:
        - `values_only` (bool): A flag indicating whether to sort the values (key-value pairs) only.
        - `show_best_match` (bool): A flag indicating whether to show the best match for the query.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Call and sort the distributions based on the specified sort type
            f = func(self, *args, **kwargs)

            # Ensure method is being implemented correctly.
            if not hasattr(self, "_sort_by"):
                raise PkgException(
                    f"The current instance {self.__class__.__name__!r} must contain a valid 'sort_by' attribute."
                )

            if best_match(self._sort_by, (0, "dates")):
                # 0 (first item) or "dates"
                sort_idx = 0
            else:
                # Default sort type is "versions"
                sort_idx = 1

            # Slice the sorted distributions based on the specified sort type
            slicer = partial(slice, *none(2))
            if best_match(self._sort_by, "reverse"):
                # Reverse the sorted distributions
                _sl = slicer(-1)
            else:
                # Default slice
                _sl = slicer(1)

            # Yield the sorted distributions based on the specified sort type
            sort_func = partial(
                lambda x: sorted(
                    x, key=None if not use_itemgetter else itemgetter(sort_idx)
                )[_sl]
            )
            if values_only:
                yield from ((pyver, sort_func(py_pkg)) for pyver, py_pkg in f)
            else:
                yield from sort_func(f)

        return wrapper

    return decorator


# endregion


# region Subclass
@cache
def subclass(*args, **kwargs) -> namedtuple:
    """
    Returns a pre-defined subclass (`NamedTuple`) for OS statistics and DateTime statistics.

    ##### Params:
        - `stats`: Returns a pre-defined subclass (`NamedTuple`) for OS statistics.
        - `date`: Returns a pre-defined subclass (`NamedTuple`) for DateTime statistics.
            - `time`: attribute to include the time in the DateTime subclass.
        - `*args`: Positional arguments for the `NamedTuple`.
        - `**kwargs`: Keyword arguments for the `NamedTuple`.

    ##### Returns:
        - `namedtuple`: Subclass for OS/DateTime statistics.

    ##### `Stats` NamedTuple Fields:
        - `symbolic` (str): Symbolic representation of the size.
        - `calculated_size` (float): Calculated size.
        - `bytes_size` (int): Size in bytes.

    ##### `DateTime` NamedTuple Fields:
        - `seconds` (float): Seconds since the epoch.
        - `full_datetime` (str): Full datetime representation.

    ##### Example:
        ```python
        st = PipMetrics.subclass(stats=True, *PipMetrics.bytes_converter(1024))
        print(st)
        # Output: Stats(symbolic='1.00 KB', calculated_size=1.0, bytes_size=1024)
        ```

        ```python
        dt = PipMetrics.subclass(date=True, *PipMetrics.datetime_converter(1631536800))
        print(dt)
        # Output: DateTime(seconds=1631536800, full_datetime='09/13/2021, 12:00:00 AM')
        ```
    """

    # Pop the 'stats' and 'date' keys from the kwargs
    # to create a NamedTuple subclass for OS/DateTime stats
    # MUST BE POPPED FIRST OR KEYS WILL BE PASSED TO THE NAMEDTUPLE
    bstats, date, _time, kwargs = popkwargs(
        "bstats", "date", "time", default_value=False, **kwargs
    )

    if all((bstats, date)):
        # Raise an exception if all 'stats' and 'date' are specified
        raise RedPkgE("Parameters 'stats' and 'date' are mutually exclusive.")

    doc_title = "NamedTuple containing {} stats with Human-readable format.\n"

    if bstats:
        # Create a NamedTuple subclass for OS stats
        st = namedtuple(
            typename="Stats",
            field_names=("symbolic", "calculated_size", "bytes_size"),
            defaults=none(3),
            module="StatsTuple",
        )
        st.__doc__ = (
            f"{doc_title.format('OS')}"
            "Fields:\n"
            "'symbolic' - Symbolic representation of the size.\n"
            "'calculated_size' - Calculated size.\n"
            "'bytes_size' - Size in bytes.\n"
        )
        return st(*args, **kwargs)

    if date:
        # Create a NamedTuple subclass for DateTime stats
        dt = namedtuple(
            typename="DateTime",
            field_names=("seconds", "date", "time"),
            defaults=none(3),
            module="DateTimeTuple",
        )
        dt.__doc__ = (
            f"{doc_title.format('DateTime')}"
            "Fields:\n"
            "'seconds' - Seconds since the epoch.\n"
            "'date' - Parsed version of the date.\n"
            "'time' - Time in human-readable format.\n"
        )
        return dt(*args, **kwargs)

    # Raise an exception if no subclass was specified
    raise PkgException("No subclass was specified.")


# endregion


# region FileUtils
def file_exists(file_path: PathOrStr, default_suffix: str) -> Path:
    """
    This function recursively checks if the file exists and creates a new file with a unique postfix if it does.
    This is to ensure that the specified file path is `valid` and `unique` to avoid overwriting existing files.

    #### Args:
        - `file_path` (PathOrStr): The file path to check.
        - `default_suffix` (str): The default suffix to use for the file.

    #### Returns:
        - `Path`: The original file path if valid,
        otherwise a new file path with a unique postfix will be returned.

    #### Raises:
        - `Exception`: An error occurred while checking the file path.
        - `OSError`: An error occurred while checking the file path.
        - `TypeError`: The file path is not a valid type.
        - `UnicodeEncodeError`: An error occurred while encoding the file path.
        - `ValueError`: The file path is not a valid value.
        - `json.JSONEncodeError`: An error occurred while encoding the file path.

    #### Example:
    ```python
    file_exists("metadata_file", "json")
    # Output: metadata_file.json

    file_exists("metadata_file.json", "json")
    # Output: metadata_file_ae9c.json
    ```
    """

    @base_exception_handler(msg=f"Failed at checking if {file_path!r} exists.")
    def recursive_filechecker(fp, ds):
        # Recursively check if the file exists and create a new file if it does.
        if not isinstance(fp, (Path, str)):
            fp = "metadata"

        fp = Path(fp)
        if fp.is_dir():
            raise RedPkgE(
                f"Invalid file path: {fp = !r}.", "\nPath must be a file type."
            )
        suffix = rm_period(fp.suffix)
        ds = ds or "txt"

        if suffix != rm_period(ds):
            fp = fp.with_suffix("." + ds)

        if not isfile(fp):
            return fp
        elif isfile(fp):
            id_codes = (generate_id(length=4, ensure_unique=True) for _ in range(2))
            id_trail = "ID" + sjoin(s="_", s_iter=id_codes)
            fp = fp.parent / f"{fp.stem}_{id_trail}"
            return file_exists(fp, default_suffix=ds)

    # Initialize the recursive filechecker
    return recursive_filechecker(file_path, default_suffix)


def exporter(
    fp: PathOrStr,
    data: Any,
    suffix: str = "",
    mode: str = "w",
    overwrite: bool = True,
    verbose: bool = True,
) -> None:
    """
    Export data to a specified file.

    This function exports the specified data to a file with the specified name and suffix.
    Depending on the suffix, the data is either written to a text file or a JSON file.

    #### Args:
        - `fp` (PathOrStr): The file path including the file name to export the data to.
        - `data` (Any): The data to export.
        - `suffix` (str): The default suffix to use for the file.

    #### Returns:
        - `None`: The result of the export.

    #### Raises:
        - `Exception`: An error occurred while exporting the data.
        - `OSError`: An error occurred while exporting the data.
        - `TypeError`: The file name is not a valid type.
        - `UnicodeEncodeError`: An error occurred while encoding the file name.
        - `ValueError`: The file name is not a valid value.
        - `json.JSONEncodeError`: An error occurred while encoding the file name.
    """
    if all((not suffix, not isinstance(suffix, str))):
        suffix = "txt"
    suffix = rm_period(suffix)
    fp = (
        Path(fp).with_suffix(f".{suffix}")
        if overwrite
        else file_exists(fp, default_suffix=suffix)
    )

    @exception_handler(
        msg=f"Failed to export {fp!r}",
        exceptions=(OSError, UnicodeEncodeError, json.JSONDecodeError),
    )
    def write_file(f):
        with open(f, mode=mode) as metadata:
            if suffix == "json":
                json.dump(data, metadata, indent=4)
            else:
                metadata.write(data)
        if verbose:
            print(f"\033[34m{f!r}\033[0m has successfully been exported.")

    write_file(fp)


def validate_file(
    file_path: PathOrStr,
    check_isfile_only: bool = False,
    is_dir: bool = False,
    include_hidden: bool = False,
) -> Union[Path, bool]:
    """
    Validate the specified file path.

    This function validates the specified file path and returns a `Path` object if the
    path is valid. If the path is invalid, a `PipException` is raised.

    #### Args:
        - `file_path` (Union[str, Path]): The file path to validate.
        - `check_isfile_only` (bool): A flag indicating whether to check if the path is a file only.
        - `is_dir` (bool): A flag indicating whether the path is a directory.
        - `include_hidden` (bool): A flag indicating whether to include hidden files.

    #### Returns:
        - `Union[Path, bool]`: A `Path` object if the path is valid.
            If `check_isfile_only` is `True`, a boolean value indicating whether the path is a file is returned.

    #### Raises:
        - `PipException`: An error occurred while validating the file path.
    """

    @base_exception_handler(msg=f"Failed at validating file {file_path}")
    def valid_file(f):
        return Path(f)

    fp = valid_file(file_path)
    if check_isfile_only:
        return all((fp.is_file(), fp.exists()))

    if not fp:
        raise PkgException(f"File arugment must not be empty: {fp =!r}")
    elif not fp.exists():
        raise PkgException(
            f"File does not exist: {fp = !r}. Please check system files."
        )
    elif all((not fp.is_file(), not fp.is_absolute())):
        raise PkgException(f"Invalid path type: {fp = !r}. Path must be a file type.")
    elif is_dir and fp.is_dir():
        raise PkgException(
            f"File is a directory: {fp = !r}. Argument must be a valid file."
        )
    elif not include_hidden and any(
        (
            search(r"^[._]", fp.stem, compiler=True),
            fp.stem.startswith((".", "_")),
        )
    ):
        print(f"Skipping {fp.name = !r}")
        return
    return fp


def isfile(fp: PathOrStr) -> Union[Path, bool]:
    """Validates and checks if the specified path is an existing file."""
    return validate_file(fp, check_isfile_only=True)


def iread(fp: PathOrStr, **kwargs):
    """Read the contents of a file."""

    @base_exception_handler(item=f"the contents for {fp!r} when trying to read it")
    def iread_(f):
        vf_params = (*get_parameters(validate_file).keys(),)
        *vf_params_values, _io_kwargs = popkwargs(
            *vf_params, default_value=False, **kwargs
        )
        vf_kwargs = {
            k: v for k, v in zip(vf_params, vf_params_values) if k != "file_path"
        }
        if validate_file(f, **vf_kwargs):
            return f.open(**_io_kwargs).read()

    if isinstance(fp, str):
        fp = Path(fp)
    return iread_(fp)


def walk_path(
    sp: PathOrStr, only_filenames: bool = True, **kwargs
) -> Generator[Any, Any, None]:
    """
    Walk the specified path and return the contents.

    #### Args:
        - `sp` (PathOrStr): The path to walk.
        - `only_filenames` (bool): A flag indicating whether to return only the filenames.
        - `**kwargs`: Keyword arguments for the `walk` method.

    #### Returns:
        - `Generator`: The contents of the specified path.
    """
    ih = kwargs.pop("include_hidden", False)
    sp_walk = validate_file(sp, include_hidden=ih).walk(**kwargs)
    yield from map(itemgetter(2), sp_walk) if only_filenames else sp_walk


def check_sitepath_suffix(pkg: str) -> bool:
    """Return a boolean value indicating whether the specified package is a site-path suffix."""
    return rm_period(Path(pkg).suffix) in ("dist-info", "py")


def get_package_name(distinfo_package: PathOrStr, stem_only: bool = False) -> str:
    """
    Return the package name for the specified distinfo package.

    #### Args:
        - `distinfo_package` (PathOrStr): The distinfo package to extract the package name from.
        Note: Any '.py' extensions will be included in the package name if 'name_only' is False.
        - `name_only` (bool): A boolean value indicating whether to return the package name only.

    #### Returns:
        - `str`: The package name for the specified distinfo package.

    #### Raises:
        - `PipException`: If the package name is not found for the specified distinfo package.

    """

    @base_exception_handler(item=f"the 'distinfo_package name for {distinfo_package!r}")
    def get_pkg_name_(d_pkg):
        path_to_str = lambda p: Path(p).stem
        if stem_only:
            return path_to_str(d_pkg)
        dpkg_name = Path(d_pkg).name.split("-")[0]
        if check_sitepath_suffix(dpkg_name):
            dpkg_name = path_to_str(dpkg_name)
        return dpkg_name

    return get_pkg_name_(distinfo_package)


def get_stem(package: PathOrStr) -> str:
    """Return the stem of the specified package."""
    return get_package_name(package, stem_only=True)


# endregion

# region OtherUtils


def bytes_unit_chart():
    return dict(
        zip(
            (
                "KB (Kilobytes)",
                "MB (Megabytes)",
                "GB (Gigabytes)",
                "TB (Terabytes)",
            ),
            (pow_(BYTES_BASE, n) for n in range(1, 5)),
        )
    )


def bytes_converter(
    num: int,
    symbol_only: bool = False,
    total_only: bool = False,
) -> Union[float, NamedTuple]:
    """
    Converts bytes to a human-readable format.

    #### Args:
        - `num` (int): Number of bytes to convert.
        - `symbol_only` (bool): Indicates whether to include only the unit symbol.
        - `total_only` (bool): Indicates whether to return only the total size.

    #### Returns:
        - `Union`[float, NamedTuple]: `float` or a `NamedTuple` containing stats with Human-readable format.
    """

    # ** (KB)-1024, (MB)-1048576, (GB)-1073741824, (TB)-1099511627776

    if not num:
        return

    if isinstance(num, str):
        try:
            num = float(num)
        except ValueError:
            raise PkgException(f"The specified value {num!r} must be an integer value.")

    results: tuple[str, float, int] = next(
        (f"{(total := num/v):.3f} {k[:2] if symbol_only else k}", total, num)
        for k, v in bytes_unit_chart().items()
        if lessthan_(num / BYTES_BASE, v)
    )
    if not total:
        # Return None if the total size was not calculated
        return
    if total_only:
        # Return the total size only
        return total
    # Return a pre-defined NamedTuple containing stats with Human-readable format
    return subclass(bstats=True, *results)


def str_to_bytes(num: Union[str, float, int], unit: str = None) -> NamedTuple:
    """
    Convert a string-like number to bytes.
    """
    if isinstance(num, str):
        if not unit:
            num, unit = num.split()

    cc = bytes_unit_chart()
    unit = find_best_match(unit, cc, default_value=next(iter(cc)))
    return bytes_converter(multiply_(float(num), cc[unit]))


def randset(rmethod: str = "sample", *args, **kwargs):
    """
    Return a random set of elements based on the specified method.

    #### Args:
        - `rmethod` (str): The random method to use.
        - `*args`: Variable-length argument list.
        - `**kwargs`: Arbitrary keyword arguments.

    #### Returns:
        - `Any`: A random set of elements based on the specified method.

    #### Raises:
        - `PipException`: An error occurred while generating a random set of elements.

    """

    @base_exception_handler(item="a random set of elements.")
    def randset_(rm):
        return getattr(SystemRandom(), rm)(*args, **kwargs)

    return randset_(rmethod)


def popkwargs(*args, **kwargs) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """
    Pop the kwarg values from a dictionary and replace them with the default value `False`.

    #### Args:
        *args: Variable-length list of keys to extract from `kwargs`.

    #### Keyword Args:
        **kwargs: Dictionary containing key-value pairs.

    #### Returns:
        *args: The extracted values corresponding to the keys provided in `args`,
        **kwargs: The remaining keyword arguments after the extraction.

    #### Example:
        >>> kwargs = {'a': 1, 'b': 2, 'c': 3}
        >>> extracted_values, remaining_kwargs = popkwargs('a', 'b', 'd', **kwargs)
        >>> print(extracted_values)
        (1, 2, None)
        >>> print(remaining_kwargs)
        {'c': 3}
    """
    df_val = kwargs.pop("default_value", None)
    return *(kwargs.pop(k, df_val) for k in args), kwargs


def search(pattern: Pattern, obj: str = "", compiler: bool = False) -> Match:
    """
    Searches for a pattern in a string or object.

    #### Args:
        - `pattern` (Pattern): The pattern to search for.
        - `obj` (Any): The object to search in.
        - `compile` (bool): Whether to compile the pattern before searching.

    #### Returns:
        - `Match`: The result of the search.

    #### Raises:
        - `PipException`:
            - The object must be a string or convertible to a string.
            - An error occurred while searching for the pattern.
    """

    # Ensure the object is a string object.
    @base_exception_handler(
        msg=f"The object {obj!r} must be a string or convertible to a string."
    )
    def check_obj(o):
        return str(o)

    obj = check_obj(obj)

    # Define the contents for creating the regex object
    re_contents = {"pattern": pattern, "flags": re.IGNORECASE}
    if compiler:
        return re.compile(**re_contents).search(obj)
    return re.search(string=obj, **re_contents)


def get_properties(
    cls: object, include_functions: bool = False
) -> Generator[tuple[str], Any, tuple[()]]:
    """
    This function inspects the given object and yields names of (cached) properties
    and functions (if set).

    #### Args:
        - `cls` (Any): The class object to inspect for (cached) properties.

    #### Returns:
        - `Generator`[str, None, None]: Names of (cached) properties.
    """
    empty = ()
    if is_class(cls):

        def get_props_(x):
            if isinstance(x, (cached_property, property)) or (
                include_functions and is_function(x)
            ):
                return x

        # Return the names of (cached) properties from the class object.
        yield from next(zip(*get_members(cls, get_props_)), empty)
    else:
        # Return an empty tuple if the object is not a class.
        return empty


def alter_if_string(
    obj: Any, return_as_tuple: bool = True
) -> Union[Any, tuple[str], str]:
    """
    Check if the specified object is a string and return it as a tuple if specified.

    #### Args:
        - `obj` (Any): The object to check.
        - `return_as_tuple` (bool): A flag indicating whether to return the object as a tuple.

    #### Returns:
        - `Any`: The object as a tuple if specified.

    """
    if isinstance(obj, (Path, str, BaseException)):
        if isinstance(obj, Path):
            obj = obj.as_posix()
        return obj if not return_as_tuple else (obj,)
    return obj


def remove_prefix(s: str, prefix: str) -> str:
    """
    Remove the specified prefix from the string.

    #### Args:
        - `s` (str): The string to remove the prefix from.
        - `prefix` (str): The prefix to remove from the string.

    #### Returns:
        - `str`: The string with the prefix removed.
    """
    try:
        return s.removeprefix(prefix)
    except BASE_EXCEPTIONS + (AttributeError,):
        return s[s.startswith(prefix) and len(prefix) :]


def best_match(
    query: str, choices: Iterable[str], *, min_ratio: int = None
) -> Union[str, None]:
    """
    Return the best match for a query from a collection of choices.

    This function uses the `fuzz.ratio` scorer from the `rapidfuzz` library to
    compare the query with each choice and return the best match.

    #### Args:
        - `query` (str): The query to match.
        - `choices` (Iterable[str]): The collection of choices to match against.

    #### Returns:
        - `str`: The best match for the query.

    #### Example 1:
    ```python
    best_match("numpy", ["numpy", "pandas", "matplotlib"])
    # Output: "numpy"
    ```

    #### Example 2:
    ```python
    best_match("paanndas", ["numpy", "pandas", "matplotlib"])
    # Output: "pandas"
    ```
    """

    @base_exception_handler(item=f"the 'best_match' for {query!r}")
    def find_match(q, c, maxr):
        l = lambda i: str(i).lower()
        # Iterate through the choices and find the best match for the query
        if match_found := process.extractOne(l(q), map(l, c), scorer=fuzz.ratio):
            # Return the best match for the query
            correct_query, mr, _ = max([match_found], key=itemgetter(1))
            if all((not maxr, not isinstance(maxr, int))):
                # Set the default max ratio value
                maxr = 95
            if mr >= maxr:
                return correct_query

    return find_match(query, alter_if_string(choices), min_ratio)


def find_best_match(key, iter_obj: Iterable, default_value: Any = None) -> Any:
    return next(
        (k for k in iter_obj if best_match(k, key, min_ratio=85)), default_value
    )


def sjoin(s_iter: Iterable[str], s: str = "") -> str:
    """
    Join the specified string iterable using the specified separator.

    #### Args:
        - `s_iter` (Iterable[str]): The string iterable to join.
        - `s` (str, optional): The separator to use for joining the strings. Defaults to an empty string.

    #### Returns:
        - `str`: The joined string iterable.
    """

    @base_exception_handler(item="the 'joined' string iterable.")
    def sjoin_(st, s_) -> str:
        return s_.join(st)

    return sjoin_(s_iter, s)


def musthave_attr(self, attr: str, item: str) -> Union[NoReturn, Literal[True]]:
    """
        Check if the specified attribute is present in the object.

        #### Args:
            - `self` (Any): The object to check.
            - `attr` (str): The attribute to check for in the object.
            - `item` (str): The item to check for in the object.
    #
        #### Raises:
            - `PipException`: An error occurred while checking for the attribute in the object.
    """
    has_attr = hasattr(self, attr)
    if not has_attr:
        raise PkgException(f"\n{self = } has no attribute {attr!r}")
    elif has_attr:
        if not getattr(self, attr):
            raise PkgException(f"\nThe {item} must be specified for this method.")
        return True


def filter_empty(iter_obj: Iterable, obj: object = "", sort_result: bool = True):
    """Filter empty values from the specified iterable object."""
    if not hasattr(obj, "__eq__"):
        raise PkgException(
            f"The specified object {obj!r} does not have an '__eq__' method."
        )
    filtered = filterfalse(obj.__eq__, iter_obj)
    if sort_result:
        filtered = sorted(filtered)
    return filtered


async def url_request(url: PathOrStr) -> Union[str, Any]:
    try:
        async with ClientSession(
            connector=TCPConnector(
                ssl=False,
                enable_cleanup_closed=True,
                force_close=True,
                ttl_dns_cache=DEFAULT_TIMEOUT,
            ),
            raise_for_status=True,
        ) as session:
            if isinstance(url, Path):
                url = url.as_posix()
            async with session.get(url) as response:
                # If the response is valid, return the response text.
                return await response.text()
    except ContentTypeError as cte:
        # If the content type is not valid, raise a `ContentTypeError`.
        raise cte
    except (ClientConnectionError, ServerDisconnectedError):
        # If the client connection is not valid, recursively retry the request.
        return await url_request(url)
    except InvalidURL:
        # If the URL is not valid, raise an `PkgException` error.
        raise RedPkgE(
            "The specified url could not be found and is considered invalid...",
            f"\n{url = }",
        )
    except ClientResponseError as cre:
        # If the client response is not valid, raise a `ClientResponseError`.
        raise cre


# endregion

__all__ = tuple(
    k
    for k, v in globals().items()
    # Constants, not private, and is a class
    if any((k.isupper(), not k.startswith("_"), is_class(k)))
    # Functions and not decorators
    and any((is_function(v), not has_decorators(v, "_cached_property")))
)
