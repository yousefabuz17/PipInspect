"""
Package Inspection and Comparison Module

This module provides a set of tools for inspecting and comparing Python packages and Python versions.
It contains a collection of functions and utility classes designed to inspect packages, compare
versions, and retrieve information from Python installations.

### Key Features
- **Inspect Packages**: Functions for retrieving details from installed Python packages.
- **Compare Versions**: Tools to compare package data across different Python versions.
- **Retrieve Installed Pythons**: Identify and list Python versions installed on a system.
- **Inspect PyPI Packages**: Retrieve information about a package from the Python Package history page.

### Main Components
- **inspect_package**: A function to inspect a package and return specified items.
- **pkg_version_compare**: A function to compare package data between two different Python versions.
- **get_version_packages**: Returns all packages installed in a specified Python version.
- **get_available_updates**: Fetches available updates for a package from the current version.
- **get_installed_pythons**: Returns a tuple of all installed Python versions.
- **inspection_fieldnames**: Lists the available fieldnames for inspection.
- **inspect_pypi**: Inspects a package on PyPI (Python Package Index) and returns the requested item.

"""


from ..pkg_modules import PkgInspect, PkgVersions
from ..pkg_utils.exception import PkgException, RedPkgE
from ..pkg_utils.utils import *


# Partial functions to exclude the generator argument
_PkgI: PkgInspect = partial(PkgInspect, generator=False)
_PkgV: PkgVersions = partial(PkgVersions, generator=False)
_PKGV_PROPS: tuple[str] = (*get_properties(PkgVersions),)


# Constants - Tuple of available fieldnames for inspection
INSPECTION_FIELDS: tuple[str] = _PkgI().get_fieldnames


def __valid_option(
    item: str,
    choices: Iterable = None,
    extras: Iterable = None,
    return_choices: bool = False,
):
    """Check if the specified item is a valid option for inspection."""
    c: Union[None, tuple[str]] = alter_if_string(choices) or _PKGV_PROPS
    if extras:
        c += alter_if_string(extras)
    option = find_best_match(item, c)
    if return_choices:
        return c, option
    return option


def __doc_handler(
    cls: Union[object, str] = None, func_name: str = None, add_doc: bool = True
):
    """Decorator to handle docstrings for functions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Call the function and return the result
            return func(*args, **kwargs)

        if add_doc:
            # Ensure func_name is set to the function name if not provided
            f_name = func_name if func_name else func.__name__

            # Retrieve the class reference and set docstring
            cls_name = (
                cls.__name__ if is_class(cls) and hasattr(cls, "__name__") else cls
            )
            cls_: object = (gg := globals().get)(cls_name, gg("PkgInspect"))
            if cls_ and hasattr(cls_, f_name):
                # Ensure the function name exists in the class
                wrapper.__doc__ = getattr(cls_, f_name).__doc__
        return wrapper

    return decorator


@__doc_handler()
def inspect_package(
    package: str = None,
    pyversion: str = None,
    *,
    itemOrfile: str = "",
    package_manager: str = None,
):
    """
    Inspect a local or PyPI package and return the requested `itemOrfile`.

    - If the `itemOrfile` is not found in the local system files, the function will attempt to inspect the package on PyPI. \
        Only if the specified `itemOrfile` is a valid option for inspection on PyPI.

    - Please refer to the `inspect_package.__doc__` for more information on inspecting packages locally and on PyPI.
    
    - Please refer to the `INSPECTION_FIELDS` constant or set `itemOrfile` to `""` for a list of available fieldnames for inspection.
    
    - Please refer to the `inspect_pypi` function for more information on inspecting packages on PyPI
    if or when the `package_manager` argument is provided.

    """
    try:
        return _PkgI(package, pyversion).inspect_package(itemOrfile)
    except ModuleNotFoundError as _mnfe_error:
        raise RedPkgE(filter_empty(_mnfe_error.args[0].splitlines())[0])
    except (*BASE_EXCEPTIONS, PkgException) as _any_e:
        try:
            return inspect_pypi(package, package_manager, item=itemOrfile)
        except PkgException as pkg_error:
            raise RedPkgE(
                f"{_any_e}\n{pkg_error.args[0]}",
                "If inspecting a package on PyPI, please refer to the 'inspect_pypi' function for more information.",
            )


@__doc_handler(func_name="version_compare")
def pkg_version_compare(
    package: str,
    first_pyversion: str,
    other_pyversion,
    /,
    *,
    item: str,
    opmethod: str = None,
):
    """
    Compare the items of a package between two different python versions.

    - If the `opmethod` is not provided, the function will return the items from both versions.

    - Please refer to the `pkg_version_compare.__doc__` for more information on comparing package data between Python versions.

    """
    return _PkgI(package, first_pyversion).version_compare(
        other_pyversion, item, opmethod=opmethod
    )


@__doc_handler()
def get_version_packages(pyversion: str) -> DateTimeAndVersion:
    """
    Get all the packages installed in a python version.

    - Please refer to the `get_version_packages.__doc__` for more information on retrieving installed packages.
    """
    return _PkgI(pyversion=pyversion).get_version_packages()


@__doc_handler(func_name="installed_pythons")
def get_installed_pythons() -> TupleOfPkgVersions:
    """
    Get all the installed python versions on the system.

    - Please refer to the `get_installed_pythons.__doc__` for more information on retrieving installed Python versions.
    """
    return _PkgI().installed_pythons


@__doc_handler(add_doc=False)
def inspect_pypi(
    package: str,
    package_manager: str = None,
    *,
    item: PyPIOptionsT = "",
) -> Union[int, DateTimeAndVersion, dict[str, DateTimeAndVersion]]:
    """
    Inspect a package on (`https://pypi.org/`) and (`https://libraries.io/`)
    and return the requested item.

    #### Args:
        - `package`: The package name to inspect.
        - `package_manager`: The package manager the package is hosted on.
            - Default: `pypi`
        - `item`: The item to return from the package.
            - Possible Options:
                - `""`: Returns all available options for inspection.
                - `initial_version`: The initial release-date and version of the package.
                - `latest_version`: The latest release-date and version of the package.
                - `package_url`: The URL of the package on PyPI.
                - `total_versions`: The total number of versions available.
                - `version_history`: A tuple of all release-date and versions available.
                - `all_items`: Returns all available items in a dictionary format.
                    - Possible Options for `all_items`:
                        - `Forks`: Returns the number of forks on GitHub.
                        - `Stars`: Returns the number of stars on GitHub.
                        - `Watchers`: Returns the number of watchers on GitHub.
                        - `Contributors`: Returns the number of contributors on GitHub.
                        - `Dependencies`: Returns the number of dependencies on GitHub.
                        - `Dependent repositories`: Returns the number of dependent repositories on GitHub.
                        - `Dependent packages`: Returns the number of dependent packages on GitHub.
                        - `Repository size`: Returns the size of the repository on GitHub.
                        - `SourceRank`: Returns the SourceRank of the package on GitHub.
                        - `Total releases`: Returns the total number of releases on GitHub.

    #### Example Output & Return State for all items: 
        - `Output Format`: dict[str, `DateTimeAndVersion`]
        - `total_versions`: Integer
        - `DateTimeAndVersion`: A NamedTuple containing the release-date and parsed version information.
            - `Representation`: ('Sep 02, 2022', '1.0.0')
            - `Attributes`:
                - `date`: The release date of the package version in `datetime` format.
                    - E.g., `datetime.datetime(2022, 9, 2, 0, 0)`
                - `version`: The version of the package in <Version> format.
                    - E.g., `<Version('1.0.0')>`
                    - `version attributes`
                        - `base_version`: Returns the version in string format.
                            - E.g., `1.0.0`
        - `version_history`: Tuple of `DateTimeAndVersion` objects
            
            NOTE: `version_history` is a `PkgGenRepr` generator object for display but will be \
                automatically unpacked to a tuple of `DateTimeAndVersion` objects when accessed. \
        
        >>> {
            'initial_version': ('Sep 02, 2022', '1.0.0'),
            'latest_version': ('Jan 01, 2024', '2.0.0'), 
            'package_url': 'https://pypi.org/project/package_name/',
            'github_stats_url': 'https://libraries.io/pypi/package_name',
            'total_versions': 1,
            'version_history': <PkgGenRepr object at 0x...>
            'github_stats': {
                'Forks': 1,
                'Stars': 1,
                'Watchers': 1329,
                'Contributors': 621,
                'Dependencies': 0,
                'Dependent repositories': '152K',
                'Dependent packages': '63.2K',
                'Repository size': Stats(symbolic='657.000 KB (Kilobytes)', calculated_size=657.0, bytes_size=672768.0),
                'SourceRank': 31,
                'Total releases': 27
                }
            }

    #### Raises:
        - `PkgException`:
            - If the `package` argument is not provided.
            - If the `package` is not found on PyPI.
            - If an error occurs while attempting to inspect the `package` on PyPI.
            - If the specified `item` is not a valid option for inspection.

    """
    if not package:
        # Raise an error if the package argument is not provided
        raise RedPkgE(
            "The 'package' argument is required to inspect a package on PyPI."
        )

    _options, _item = __valid_option(
        item,
        extras=(
            _empty := "",
            _all_items_str := "all_items",
            _gh_str := "github_stats",
            *(gh_stat_keys := PkgVersions.gh_stat_keys()),
        ),
        return_choices=True,
    )
    options = filter_empty(_options)
    
    if _item is None:
        if find_best_match(item, INSPECTION_FIELDS):
            #! DO NOT REMOVE
            # For 'inspect_package' function purposes
            raise PkgException("")
        raise RedPkgE(
            f"The specified item {item!r} is not a valid option for inspection."
        )
    elif _item == _empty or not any(filter_empty((item, _item))):
        # Return all available options for inspection
        # if no item is specified
        return options

    # Return the requested item from the package
    if all((package, _item)):
        pypi_item = lambda it: getattr(
            _PkgV(package, package_manager=package_manager), it
        )

        if _item == _all_items_str:
            # Return all available items in a dictionary format
            return {k: pypi_item(k) for k in _PKGV_PROPS}
        elif _item in _PKGV_PROPS:
            # Return the requested item from the package
            return pypi_item(_item)
        elif _item in (*gh_stat_keys, _gh_str):
            get_gh_stats = lambda x=_gh_str: pypi_item(x)
            if _item == _gh_str:
                # Return the GitHub statistics for the package
                return get_gh_stats()
            # Or the specified item from the GitHub statistics
            return get_gh_stats()[_item]


@__doc_handler(cls=PkgVersions, func_name="get_updates")
def get_available_updates(
    package: str, current_version: str = None, *, include_betas: bool = False
):
    """
    Fetch the available updates from the specified current version of the package.

    - Please refer to the `get_available_updates.__doc__` for more information on fetching updates.

    """

    if include_betas:
        raise NotImplementedError(
            "\033[1;31mBeta (pre-release) versions for packages are currently not supported yet and will be ignored when checking for updates.\033[0m"
        )

    if current_version is None:
        _pkg_i = partial(_PkgI, package=package)
        i_pythons = _pkg_i().installed_pythons
        current_version = _pkg_i(pyversion=i_pythons[-1]).installed_version
    return _PkgV(package).get_updates(current_version)


__all__ = ("INSPECTION_FIELDS",) + (
    *(
        k
        for k, v in globals().items()
        # All 'pkg_functions.functions' functions
        if all((is_function(v), has_decorators(v)))
    ),
)
