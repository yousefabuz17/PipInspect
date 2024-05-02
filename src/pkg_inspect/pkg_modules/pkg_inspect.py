import site

from .pkg_metrics import PkgMetrics as PkgM
from .pkg_versions import PkgVersions as PkgV
from ..pkg_utils.exception import PkgException, RedPkgE
from ..pkg_utils.utils import *


# region _PInspect
class _PkgInspect:
    """
    This base class provides the core functionality for retrieving the installed Python packages and versions.

    #### Properties:
        - `site_packages`: Returns the site packages installed for each Python version.
        - `package_paths`: Returns the site-package dist-info paths for each Python version.
        - `package_versions`: Returns the package versions installed for each Python version.
        - `pyversions`: Returns the installed Python versions (Python version directories).
        - `installed_pythons`: Returns the installed Python versions as a `tuple[int, ...]`.
    """

    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_generator",
        "_workers",
        "_sort_by",
        "_pyversions",
        "_package_paths",
        "_site_packages",
        "_package_versions",
        "_installed_pythons",
    )

    def __init__(
        self,
        generator: bool = True,
        *,
        max_workers: int = None,
        sort_by: Union[ZeroOrOne, Literal["reverse"]] = 0,
    ) -> None:
        # Arguments
        self._generator = generator
        self._workers = max_workers
        self._sort_by = sort_by

        # Attributes
        self._pyversions = None
        self._package_paths = None
        self._site_packages = None
        self._package_versions = None
        self._installed_pythons = None

    def __repr__(self) -> str:
        """
        #### Returns:
            - `str`: A string representation of the `PkgInspect` instance, displaying the inspected Python versions.

        #### Example:
            ```python
            >>> PkgInspect()

            # Output:
            [Inspected Python Versions]
            ('3.8', '3.9', '3.10', ...)

            >>> PkgInspect(generator=False)

            # Output:
            [Inspected Python Versions]
            ('3.8', '3.9', '3.10', ...)
            [Total Inspected Packages - PYVersion ('3.12')]
            227
            ```
        """
        return "[Inspected Python Versions]\n" f"{(*self._get_installed_pythons(),)}\n"

    @staticmethod
    def _vparser(v) -> PackageVersion:
        return PkgV.parse_version(v)

    @classmethod
    @exception_handler("site-path version number", exceptions=StopIteration)
    def _get_version_num(
        cls,
        site_path: Union[Path, str],
        dist_ver: bool = False,
    ) -> Optional[PackageVersion]:
        if not site_path:
            # Return None if the site path is not specified
            return
        else:
            # Convert the site path to a 'Path' object if it is a string
            site_path = Path(site_path)

        if dist_ver:
            # Extract the version number from the dist-info package name
            version_num = search(
                pattern=PkgV.VERSION_PATTERN, obj=site_path.name, compiler=True
            )
            version = version_num.group() if version_num else None
        else:
            # Extract the version number from the site-packages path
            version = next((i for i in site_path.parts if search(r"\d\.\d+", i)), None)

        if version:
            # Parse the version number if found
            return cls._vparser(version)

    @base_exception_handler(item="the distinfo package-paths")
    def _get_package_paths(self) -> Generator[tuple[Any, set], Any, None]:
        pyver_packages = (
            (
                # Python version
                self._get_version_num(p),
                # Generator of '.dist-info' or '.py' file package paths
                (
                    pkg
                    for pkg in p.glob("*")
                    if all(
                        (
                            # Check if the package is not a framework package
                            not search(r"pyobjc", pkg),
                            # Check if the package is a '.dist-info' or '.py' file
                            check_sitepath_suffix(pkg),
                        )
                    )
                ),
            )
            for p in self._get_site_packages()
        )

        # Iterate over the Python version and the package paths
        for ver, ver_pkgs in pyver_packages:
            # Get the package paths for the specified Python version
            package_paths = set()
            # Iterate over the package paths
            for ver_pkg in ver_pkgs:
                # Ensure that the package name is unique
                # Some packages may be a '.py' file and a '.dist-info' path
                pkg_name = get_package_name(ver_pkg)
                if pkg_name not in package_paths:
                    # Add the package name to the set
                    # This is to ensure that the package name is unique
                    package_paths.add(pkg_name)
                if pkg_name in package_paths:
                    # Remove the package name to be replaced with the package path
                    package_paths.discard(pkg_name)
                    # Add the package path instead
                    package_paths.add(ver_pkg)
            # Yield the Python version and the package paths
            yield ver, package_paths

    @base_exception_handler(item="the site-packages")
    def _get_site_packages(self) -> Iterable[Path]:
        yield from (
            v_path / v_dir.relative_to(v_path)
            for v_path in self._get_versions()
            for v_dir in v_path.rglob("site-packages")
        )

    @base_exception_handler(item="the python versions")
    def _get_versions(self) -> Generator[Path, None, None]:
        sitep_path = Path(site.getsitepackages()[0]).parts
        version_path = "/".join(sitep_path[: sitep_path.index("Versions") + 1])[1:]
        yield from (
            p
            for p in Path(version_path).glob("*")
            if p.is_dir() and self._get_version_num(p)
        )

    def _ver_executor(
        self, distinfo_package: Path
    ) -> Generator[tuple[Any, str], Any, None]:
        def _check_version(d_package) -> tuple[Any, str]:
            package_name = get_package_name(d_package)
            package_ver = self._get_version_num(d_package, dist_ver=True)
            if package_ver is None:
                # Import the version number if the version number is not found
                # Otherwise, will return Version("0.0.0.0") by default.
                package_ver = PkgV.import_version(package_name, parse_version=True)
            return package_name, package_ver

        packages = executor(
            _check_version,
            distinfo_package,
            max_workers=self._workers,
        )
        yield from sorted(packages)

    def _get_package_versions(
        self,
    ) -> Generator[tuple[str, tuple[tuple[Any, str]]], None, None]:
        yield from (
            # E.g (3.12, (<packages>))
            (py_ver, self._ver_executor(package))
            for py_ver, package in self._get_package_paths()
        )

    def _get_package_names(
        self,
        py_version: str,
        *,
        return_total: bool = False,
        **kwargs,
    ) -> Union[list[str], Any]:
        py_version = self._check_version(py_version)
        raps = kwargs.pop("return_as_paths", True)
        pyver_packagenames = sorted(
            # Get the package names for the specified Python version
            py_pack if raps else get_package_name(py_pack)
            # pyver: Python version, pyver_packages: Package paths
            for pyver, pyver_packages in self._get_package_paths()
            # py_pack: Package path
            for py_pack in pyver_packages
            # Check if the Python version matches the specified version
            if pyver == py_version
        )

        if not pyver_packagenames:
            # Raise an exception if no packages were found for the specified Python version
            raise PkgException(
                f"No packages were found for the specified Python version {py_version!r}"
            )

        if return_total:
            # Return the total number of packages
            # found for the specified python version
            return len(pyver_packagenames)

        # Return the sorted package names
        return pyver_packagenames

    def _check_package(self, py_version: str, package_name: str):
        """
        Check the package name for the specified Python version.
        This method is to ensure that the package is found in the specified Python version.

        #### Args:
            - `py_version` (str): The Python version to search for the package.
            - `package_name` (str): The package name to search for.

        #### Returns:
            - `str`: The package name for the specified Python version.

        #### Raises:
            - `PkgException`: If the package is not found in the specified Python version.

        """
        py_version = self._check_version(py_version)

        try:
            # Check if the package is found in the specified Python version
            return next(
                pkg
                for pkg in self._get_package_names(
                    py_version=py_version, return_as_paths=False
                )
                if best_match(pkg, package_name)
            )
        except StopIteration:
            # Raise an exception if the package is not found
            raise PkgException(
                f"The package ({package_name!r}) was not found in the specified Python version {py_version!r}"
            )

    def _check_version(
        self, py_version: str, allow_none: bool = False
    ) -> Union[PackageVersion, None]:
        """
        Check the version number for the specified Python version.
        This method is to ensure that the version number is found for the specified Python version.

        #### Args:
            - `py_version` (str): The Python version to search for the version number.

        #### Returns:
            - `str`: The version number for the specified Python version.

        #### Raises:
            - `PkgException`: If the version number is not found for the specified Python version.

        """
        if not py_version and allow_none:
            # Return None if the version number is not specified
            # and 'allow_none' is set to True
            return

        # Validate and parse the Python version
        py_version = self._vparser(py_version)
        if py_version not in self._get_installed_pythons():
            # Raise an exception if the version number is not found
            raise PkgException(
                f"The specified Python version ({py_version = }) is either not installed or cannot not found."
            )
        return py_version

    @cache
    def _get_site_package(self, other_pkg: str = None, other_pyv: str = None) -> Path:
        """
        Get the site package for the specified Python version and package name.

        #### Returns:
            - `Path`: The site package for the specified Python version and package name.
        """
        # Check if the package/pyversion is specified
        pyv = self._check_version(other_pyv)
        pkg = self._check_package(pyv, other_pkg)

        # Return the site package path for the specified package
        # Otherwise, will raise a 'PkgException' if the package is not found
        return next(
            distinfo_pkg
            for distinfo_pkg in self.get_version_packages()
            if search(pkg, get_stem(distinfo_pkg), compiler=True)
        )

    @property
    @generator_handler()
    @sort_distributions(use_itemgetter=False)
    def site_packages(self) -> tuple[tuple[str, Generator[Path, None, None]], ...]:
        """
        Returns the site packages installed for each Python version.

        #### Example:
        >>> <generator object PkgInspect._get_package_paths.<locals>.<genexpr> at 0x...>
        >>> (PosixPath('/usr/local/Cellar/python@3.8/3.8.2_2/Frameworks/Python.framework/Versions/3.8/lib/python3.8/site-packages'), ...)
        """
        if self._site_packages is None:
            self._site_packages = self._get_site_packages()

        return self._site_packages

    @property
    @generator_handler()
    @sort_distributions()
    def package_paths(self) -> Union[Iterable[Path], tuple]:
        """
        Returns the site-package dist-info paths for each Python version.

        #### Example:
        >>> ('3.8', <generator object PkgInspect._ver_executor at 0x...>, ...)
        >>> ('3.8', [PosixPath('/usr/local/Cellar/python@3.8/3.8.2_2/Frameworks/Python.framework/Versions/3.8/lib/python3.8/site-packages/pip-20.0.2.dist-info'), ...])
        """
        if self._package_paths is None:
            self._package_paths = self._get_package_paths()
        return self._package_paths

    @property
    @generator_handler()
    @sort_distributions(values_only=True)
    def package_versions(
        self,
    ) -> Union[
        Generator[tuple[str, tuple[tuple[str, ...]]], None, None],
        tuple[tuple[str, ...]],
    ]:
        """
        Returns the package versions installed for each Python version.

        ##### Example:

        >>> ('3.8', <generator object PkgInspect._ver_executor at 0x...>)
        >>> ('3.8', (('pip', '20.0.2'), ('setuptools', '46.1.3'), ('wheel', '0.34.2'), ...))
        """
        if self._package_versions is None:
            self._package_versions = self._get_package_versions()
        return self._package_versions

    def _get_installed_pythons(self) -> Generator[Optional[PackageVersion], None, None]:
        yield from (self._get_version_num(pyv) for pyv in self._get_versions())

    @property
    @generator_handler()
    @sort_distributions(use_itemgetter=False)
    def pyversions(self) -> Generator[Path, None, None]:
        """
        Returns all directories for the installed Python versions.

        #### Example:

        >>> [PosixPath('/usr/local/Cellar/python@3.8/3.8.2_2/Frameworks/Python.framework/Versions/3.8'), ...]
        """

        if self._pyversions is None:
            self._pyversions = self._get_versions()
        return self._pyversions

    @property
    @generator_handler()
    @sort_distributions(use_itemgetter=False)
    def installed_pythons(self) -> TupleOfPkgVersions:
        """
        Returns the installed Python versions.

        #### Example:

        >>> (<Version('3.8')>, <Version('3.9')>, <Version('3.10')>, ...)
        """

        if self._installed_pythons is None:
            self._installed_pythons = self._get_installed_pythons()
        return self._installed_pythons


# endregion


# region PInspect
class PkgInspect(_PkgInspect):
    """
    A class for inspecting installed Python packages and versions.

    #### Args:
        - `package` (PathOrStr): The package name to inspect.
        - `pyversion` (str): The Python version to inspect.
        - `generator` (bool): A boolean value indicating whether to return a generator or unpacked result.
        - `max_workers` (int): The maximum number of workers to use for concurrent execution.
            (`ThreadPoolExecutor`)
        - `sort_by` (Union[ZeroOrOne, Literal["reverse"]]): A value indicating whether to sort the distributions.

    #### Attributes:
        - `package_paths` (Iterable[Path]): Property for site-package paths for each python version.
        - `package_versions` (Generator[tuple[str, tuple[tuple[Any, str]]]]): Property for package versions installed for each python version.
        - `pyversions` (tuple[Path]): Property for installed python versions.
        - `site_packages` (Iterable[str]): Property for site packages installed for each python version.

    #### Methods:
        - `inspect_package`: Inspect details of an installed Python package.
        - `_check_package`: Check the package name for the specified Python version.

    #### Examples:
        ```python
        # The `inspect_package` method is called to inspect the details of the `pkgInspect` package.
        PkgInspect().inspect_package(package="pkgInspect", item="short_meta")
        # Output: {'Metadata-Version': 'x.x', 'Name': 'pkgInspect', 'Version': '1.x.x', 'Summary': 'A powerful data analysis and manipulation library for Python.', 'Home-page': 'https://pandas.pydata.org', 'Author': 'Wes McKinney', 'Author-email': '

        PkgInspect().inspect_package(package="pkgInspect", item="version")
        # Output: '1.x.x'

        PkgInspect().inspect_package(package="pkgInspect", item="license")
        # Output: 'Apache 2.0'

        PkgInspect().inspect_package(package="pkgInspect", item="version_history")
        # Output: (('1.x.x', 'Jan 1, 2021'), ('1.x.x', 'Dec 1, 2020'), ...)

        # Attrbutes
        PkgInspect().pyversions
        # Output: ('3.8', '3.9', '3.10', ...)

        PkgInspect().package_paths
        # Output:
        # ('3.8', <generator object PkgInspect._ver_executor at 0x...>, ...)
        # ('3.8', [PosixPath('/usr/local/Cellar/python@3.8/3.8.2_2/Frameworks/Python.framework/Versions/3.8/lib/python3.8/site-packages/pip-20.0.2.dist-info'), ...])

        PkgInspect().site_packages
        # Output:
        # <generator object PkgInspect._get_site_packages at 0x...>
        # (PosixPath('/usr/local/Cellar/python@3.8/3.8.2_2/Frameworks/Python.framework/Versions/3.8/lib/python3.8/site-packages'), ...)

        PkgInspect().package_versions
        # Output:
        # ('3.8', <generator object PkgInspect._ver_executor at 0x...>)
        # ('3.8', (('pip', '20.0.2'), ('setuptools', '46.1.3'), ('wheel', '0.34.2'), ...))
        ```
    """

    __dict__ = {}
    __slots__ = ("__weakrefs__", "_pyversion", "_pkg", "__pipv_pkg", "__pipm")

    def __init__(
        self, package: PathOrStr = None, pyversion: str = None, **kwargs
    ) -> None:
        # kwargs: 'generator', 'max_workers', 'sort_by'
        super().__init__(**kwargs)
        self._pyversion = self._check_version(pyversion, allow_none=True)
        self._pkg = (
            self._check_package(
                py_version=self._pyversion,
                package_name=get_package_name(package),
            )
            if all((self._pyversion, package))
            else None
        )
        self.__pipm: PkgM = partial(PkgM, max_workers=self._workers)
        if self._pkg:
            self.__pipv_pkg: PkgV = lambda: PkgV(
                package=self._pkg, generator=self._generator
            )

    @recursive_repr(fillvalue="PkgInspect(...)")
    def __repr__(self) -> str:
        return PkgGenRepr(self).__str__()

    def __str__(self) -> str:
        """
        Return a string representation of the `PkgInspect` instance.

        #### Returns:
            - `str`: A string representation of the `PkgInspect` instance, displaying the inspected Python versions.

        #### Example:
        ```python
        >>> PkgInspect()
        # Output:
        [Inspected Python Versions]
        ('3.8', '3.9', '3.10', ...)
        ```
        """
        if not self._generator and self._pyversion:
            return super().__repr__()
        return self.__repr__()

    def __check_attrs(self, attr: str = None):
        _musthave = lambda at: musthave_attr(
            self, attr=at, item="Python {!r}".format(at.lstrip("_"))
        )
        if attr and attr in self.__slots__:
            _musthave(attr)
            return
        else:
            _musthave("_pyversion")
            _musthave("_pkg")

    @cache
    def _import_meta(
        self, package: str = None, *, item: str = None
    ) -> Union[str, Any, None]:
        args = (doc := "doc", src_file := "source_file", src_code := "source_code")
        import_module = importlib.import_module

        def has_doc(c_obj, import_=True) -> Union[str, None]:
            cobj = c_obj if not import_ else import_module(c_obj)
            cobj_args = (cobj, "__doc__")
            if all(
                (
                    item == doc,
                    hasattr(*cobj_args),
                    getattr(*cobj_args),
                )
            ):
                return cobj.__doc__

        try:
            cls_obj = import_module(package)
            if _item := find_best_match(item, args):
                if _item in (src_code, src_file):
                    src_file_path = get_sourcefile(cls_obj)
                    if _item == src_code:
                        return iread(src_file_path, include_hidden=True)
                    return src_file_path
                if found_doc := has_doc(cls_obj, import_=False):
                    return found_doc

                possible_pkg = Path(__import__(package).__file__).parent.stem
                return has_doc(possible_pkg)

        except ModuleNotFoundError:
            site_pkg = self._get_site_package(package, self._pyversion)
            for filenames in walk_path(site_pkg):
                for file in filenames:
                    if get_stem(file).lower() == "top_level":
                        possible_pkg = iread(site_pkg / file).splitlines()[0]
                        return has_doc(possible_pkg)

    @staticmethod
    @cache
    def __short_metadata(metadata_contents: str) -> dict[str, str]:
        # Parse the metadata contents
        # into a dictionary of the most important metadata fields.

        # 'Platforms' & 'Classifiers'
        # These fields may contain multiple values, so we need to handle them separately.
        clsifier_pltform = "Classifier", "Platform"

        def _split(pair, m="split", k=None):
            # Split the metadata contents
            # E.g
            #   - ('Author', 'Yousef Abuzahrieh')
            #   - ('Classifier', 'Programming Language Python 3 Only')
            clsifier = clsifier_pltform[0]
            s = ": "
            if k == clsifier:
                s = " "
            key_pair = getattr(pair, m)(s if m == "split" else "")
            if k == clsifier:
                # Clean the classifier field
                # E.g 'Programming Language :: Python :: 3 :: Only' -> 'Programming Language Python 3 Only'
                _kp = re.sub(r"\s+", " ", clean(" ".join(key_pair)))
                key_pair = _kp.split(" ", 1)
            return key_pair

        short_m = clone_gen(
            (
                _split(i, k=k)
                for i in _split(metadata_contents, "splitlines")
                if best_match(k := _split(i)[0], METADATA_FIELDS) and k[0].isupper()
            ),
            iter_only=True,
        )

        short_m_contents = {}
        add_s = lambda a: add_(a, "s")

        def _join_contents(key, contents=None):
            values = set()
            for k, v in next(contents):
                if k == key:
                    values.add(v)
                short_m_contents[k] = v
            if values:
                if len(values) > 1:
                    key = add_s(key)

                short_m_contents[key] = values

                def _key_cleaner(_k):
                    # Remove the single key if multiple values were found
                    if {_k, add_s(_k)} <= set(short_m_contents):
                        short_m_contents.pop(_k)

                for _rk in clsifier_pltform:
                    _key_cleaner(_rk)
                # Return the short metadata contents
                return short_m_contents
            # Otherwise, return the empty set
            return values

        # Join the contents of the metadata fields into a single dictionary.
        for _rs in clsifier_pltform:
            _join_contents(_rs, contents=short_m)
        return short_m_contents

    @cache
    def inspect_package(self, itemOrfile: str = "") -> Optional[Any]:
        """
        This method can be used to extract specific details about an installed Python package.

        #### NOTE:
            - If `itemOrfile` is an empty string, the method will return all available fieldnames (options) as a sorted list.
            - The `itemOrfile` parameter must be a string type value of the item or file name to inspect from the package.
                - If the `itemOrfile` is a file name, the method will return the contents of the file.
                    - If the specified file name is not within METADATA_FIELDS, the method will walk \
                        through the packages directory to find the file.
            - The `itemOrfile` parameter uses fuzzy matching to find the closest match.
                - E.g., 'short_meta' will match 'Short Meta', 'short_meta', 'short-meta', etc.
                #### NOTE: Please ensure that the field name specified closely matches \
                    one of the available field names to prevent errors or inaccuracies.
            - [EXPERIMENTAL] Document Retrieval
                - Retrieving the packages documentation is not supported for all packages.
                - The method will attempt to retrieve the documentation from the package using various methods:
                    - importing the packing and using the `__doc__` attribute
                    - using the `inspect` module
                    - reading the top level source file from `top_level.txt`.
                - If the documentation is not found, the method will return None.

        #### LEGEND for `itemOrfile` (Return Type):
            - `PackageVersion`: (Type[package_version.Version])
            - `TupleOfPkgVersions`: (tuple[`PackageVersion`, ...])
            - `DateTimeAndVersion`: (tuple[Union[datetime, `PackageVersion`]])
        
        #### Arg:
            - `itemOrfile` (str): The item or file name to inspect from the specified package.
                - Possible Options -> (`itemOrfile` (Return Type)):
                    - `short_meta` (dict[str, Any]): Returns a dictionary of the most important metadata fields.
                        - If only one field is needed, you can use any of the following metadata fields.
                        - Possible Fields instead of `short_meta`:
                            - `Metadata-Version` (PackageVersion)
                            - `Name` (str)
                            - `Summary` (str)
                            - `Author-email` (str)
                            - `Home-page` (str)
                            - `Download-URL` (str)
                            - `Platform(s)` (set)
                            - `Author` (str)
                            - `Classifier(s)` (set)
                            - `Description-Content-Type` (str)
                    - `short_license` (str): Returns the name of the license being used.
                    - `metadata` (str): Returns the contents of the METADATA file.
                    - `installer` (str): Returns the installer tool used for installation.
                    - `license` (str): Returns the contents of the LICENSE file.
                    - `record` (str): Returns the list of installed files.
                    - `wheel` (str): Returns information about the Wheel distribution format.
                    - `requested` (str): Returns information about the requested installation.
                    - `authors` (str): Returns the contents of the AUTHORS.md file.
                    - `entry_points` (str): Returns the contents of the entry_points.txt file.
                    - `top_level` (str): Returns the contents of the top_level.txt file.
                    - `source_file` (str): Returns the source file path for the specified package.
                    - `source_code` (str): Returns the source code contents for the specified package.
                    - `doc` (str): Returns the documentation for the specified package.

                    - `Pkg` Custom Class Fields
                        - `PkgInspect fields`: Possible Fields from the `PkgInspect` class.
                            - `site_path` (Path): Returns the site path of the package.
                            - `package_paths` (Iterable[Path]): Returns the package paths of the package.
                            - `package_versions` (Generator[tuple[str, tuple[tuple[Any, str]]]]): Returns the package versions of the package.
                            - `pyversions` (tuple[Path]): Returns the Python versions of the package.
                            - `installed_pythons` (TupleOfPkgVersions): Returns the installed Python versions of the package.
                            - `site_packages` (Iterable[str]): Returns the site packages of the package.
                            - `islatest_version` (bool): Returns True if the package is the latest version.
                            - `isinstalled_version` (bool): Returns True if the package is the installed version.
                            - `installed_version` (PackageVersion): Returns the installed version of the package.
                            - `available_updates` (TupleOfPkgVersions): Returns the available updates of the package.

                        - `PkgVersions fields`: Possible Fields from the `PkgVersions` class.
                            - `initial_version` (PackageVersion): Returns the initial version of the package.
                            - `installed_version` (PackageVersion): Returns the installed version of the package.
                            - `latest_version` (PackageVersion): Returns the latest version of the package.
                            - `total_versions` (int): Returns the total number of versions of the package.
                            - `version_history` (TupleOfPkgVersions): Returns the version history of the specified package.
                            - `package_url`: Returns the URL of the package on PyPI.
                            - `github_stats_url` (str): Returns the GitHub statistics URL of the package.
                            - `github_stats` (dict[str, Any]): Returns the GitHub statistics of the package.
                                - The GitHub statistics are returned as a dictionary \
                                    containing the following fields which can accessed using the `item` parameter:
                                    - `Forks` (int): Returns the number of forks on GitHub.
                                    - `Stars` (int): Returns the number of stars on GitHub.
                                    - `Watchers` (int): Returns the number of watchers on GitHub.
                                    - `Contributors` (int): Returns the number of contributors on GitHub.
                                    - `Dependencies` (int): Returns the number of dependencies on GitHub.
                                    - `Dependent repositories` (int): Returns the number of dependent repositories on GitHub.
                                    - `Dependent packages` (int): Returns the number of dependent packages on GitHub.
                                    - `Repository size` (NamedTuple): Returns the size of the repository on GitHub.
                                    - `SourceRank` (int): Returns the SourceRank of the package on GitHub.
                                    - `Total releases` (int): Returns the total number of releases on GitHub.
                        
                        - `PkgMetrics fields`: Possible Fields from the `PkgMetrics` class.
                            - `all_metric_stats` (dict[str, Any]): Returns all the OS statistics of the package.
                            - `total_size` (int): Returns the total size of the package.
                            - `date_installed` (datetime): Returns the date the package was installed.
                                - NOTE: Will return either the 'st_birthtime' or 'st_ctime' of the package \
                                    depending on the OS.
                        
                        - `pypistats fields`: Possible Fields from the `pypistats` module.
                            - `all-pypi-stats` (dict[str, Any]): Returns all the statistics of the package on PyPI into a single dictionary.
                            - `stats-overall` (dict[str, Any]): Returns the overall statistics of the package on PyPI.
                            - `stats-major` (dict[str, Any]): Returns the major version statistics of the package on PyPI.
                            - `stats-minor` (dict[str, Any]): Returns the minor version statistics of the package on PyPI.
                            - `stats-recent` (dict[str, Any]): Returns the recent statistics of the package on PyPI.
                            - `stats-system` (dict[str, Any]): Returns the system statistics of the package on PyPI.
                                - NOTE: The 'pypistats' module must be installed to retrieve the statistics. \
                                    Otherwise, an exception will be raised. The field names prefixes are customzied \
                                        for retrieval purposes but will respectively return the original field names contents.

                    - `Others`:
                        - `""` or `get_fieldnames`: Returns all available fieldnames (options) as a tuple.
                            - `NOTE`: Can also be retrieved from importing `INSPECTION_FIELDS` constant.
        
        #### NOTE Any other field name will be treated as a file name to inspect from the packages' directory.

        #### Returns:
            - `Any`: The requested item for the specified package.

        #### Raises:
            - `PkgException`:
                - If the specified item is not a string type.
                - If the specified package or Python version is not found.
        """

        if itemOrfile is None or not isinstance(itemOrfile, str):
            # Raise an exception if the item is not a string type
            raise RedPkgE(
                f"({itemOrfile = }) is not a valid option item for inspection and must be a string-type value."
            )

        # All options for inspection fields
        insp_fields: tuple[str] = (
            empty := "",
            sp := "site_path",
            *METADATA_FIELDS,
            *(shorts := ("short_license", "short_meta")),
            *(pkgv_props := (*get_properties(PkgV), *(gh_keys := PkgV.gh_stat_keys()))),
            *(
                inspect_fields := (
                    "doc",
                    "source_file",
                    "source_code",
                )
            ),
            *(
                pkgm_props := (
                    di := "date_installed",
                    *get_properties(PkgM),
                    *(st_fields := self.__pipm().get_metrickeys),
                )
            ),
            *(
                pkgi_props := (
                    *{
                        gvp := "get_version_packages",
                        *get_properties(PkgInspect),
                        *(__pkgi_props := (*get_properties(__pkgi := _PkgInspect),)),
                    },
                )
            ),
            *(
                pypistats_props := (
                    "stats-overall",
                    *(mm := ("stats-major", "stats-minor")),
                    "stats-recent",
                    "stats-system",
                    aps := "all-pypi-stats",
                )
            ),
        )

        _item: Optional[Any] = find_best_match(itemOrfile, insp_fields)

        if itemOrfile == empty or _item == "get_fieldnames":
            # Return the metadata fields if no item is specified
            return filter_empty(insp_fields)

        # Seperating '_PkgInspect' conditional statements
        # to prevent from validating unrelevant args.
        if _item in (gvp, *__pkgi_props):
            if _item == gvp:
                return getattr(self, _item)(return_as_paths=True)
            return getattr(__pkgi(generator=False), _item)

        elif _item in pypistats_props:
            # Check if the package is specified
            self.__check_attrs(attr="_pkg")
            rm_stats_prefix = partial(remove_prefix, prefix="stats-")

            @exception_handler(
                msg=f"The 'pypistats' module must be installed to retrieve the {_item!r} item.",
                exceptions=(AttributeError, ModuleNotFoundError),
                raise_with=ModuleNotFoundError,
            )
            def _get_pypistat(item_obj):
                # Return the specified item from the 'pypistats' module into a dictionary.
                p_stats_json = json.loads(
                    getattr(pypistats, item_obj)(self._pkg, format="json")
                )
                return {p_stats_json["type"]: p_stats_json["data"]}

            def _fix_keys(item_obj):
                if item_obj in map(rm_stats_prefix, mm):
                    item_obj = "python_" + item_obj
                return item_obj

            # Check if the item is a property of the 'pypistats' module
            if _item != aps:
                _item = rm_stats_prefix(_item)

            # Fix the keys for the statistics
            _item = _fix_keys(_item)

            if _item == aps:
                # Return all the statistics from the 'pypistats' module
                # in a dictionary format.
                full_pypi_stats = {}
                _pypi_methods = [
                    *map(rm_stats_prefix, pypistats_props),
                ]
                # Iterate over the 'pypistats' module properties
                for m in _pypi_methods:
                    # Fix the keys for the statistics
                    m = _fix_keys(m)
                    if m != aps:
                        # Update the dictionary with the statistics
                        full_pypi_stats.update(**_get_pypistat(m))
                # Return the full statistics
                return full_pypi_stats
            # Otherwise, return the specified item from the 'pypistats' module
            return _get_pypistat(_item)

        # The following options require the package to be specified
        # and the Python version to be specified and validated.
        self.__check_attrs()

        if _item in pkgv_props:
            get_pkgv = lambda it: getattr(self.__pipv_pkg(), it)
            if _item in gh_keys or _item == (gh_stats_str := "github_stats"):
                gh_stats = lambda x=gh_stats_str: get_pkgv(x)
                if _item == gh_stats_str:
                    return gh_stats()
                return gh_stats()[_item.capitalize()]
            # Check if the item is a property of the 'PkgVersions' class
            return get_pkgv(_item)
        elif _item in pkgi_props:
            return getattr(self, _item)
        elif _item in inspect_fields:
            # Return the source file for the specified package
            return self._import_meta(self._pkg, item=_item)

        # dist-info site path
        site_path: Path = self.get_site_package()

        if _item == sp:
            # Return the site path for the specified package
            return site_path
        elif _item in pkgm_props:
            # Check if the item is a property of the 'PkgMetrics' class
            pkgm_cls = self.__pipm(alter_if_string(site_path))
            if _item == di:
                # Return the date the package was installed
                return pkgm_cls.date_installed(self._pkg)
            elif _item in st_fields:
                return pkgm_cls.all_metric_stats[self._pkg].get(_item)
            # Otherwise, return the specified field from the 'PkgMetrics' class
            return getattr(pkgm_cls, _item)

        # Read the contents of the specified file
        read_file = lambda fp: iread(site_path / fp)

        # Search for the specified item in the package directory
        # Walk through the package directory to check if 'itemOrfile' is a:
        #   1. file name within the packages directory
        #   2. METADATA field names (e.g 'Name', 'Summary', 'Author', etc.)
        #   3. short metadata field names (e.g 'short_meta', 'short_license')
        #   4. not found in the package directory, search the original specified 'itemOrfile' \
        #        in the package directory for the possible file name.
        for file_names in walk_path(site_path):
            for file in file_names:
                # If _item is not within the possible inspection field values
                # search the original specified 'itemOrfile'
                # in the package directory
                find_file = partial(search, obj=file)
                if _item is None and find_file(itemOrfile):
                    return read_file(file)
                elif _item:
                    found_file = find_file(_item)
                    # Check if the item is found and is not a short metadata field
                    if found_file and _item not in shorts:
                        # If the item is found as is a file
                        # return the contents of the file
                        return read_file(file)

                    # Check if the item is a metadata field or a short metadata field
                    elif not found_file and search("metadata", file):
                        # Retrieve contents relative to the 'METADATA' file
                        short_meta: dict = self.__short_metadata(read_file(file))
                        if (_mv := "Metadata-Version") in short_meta:
                            # Parse the Metadata-Version
                            short_meta[_mv] = self._vparser(short_meta[_mv])

                        if _item in shorts:
                            # Return either the short metadata or the short license
                            return [short_meta, short_meta.get("License")][
                                _item == shorts[0]
                            ]

                        sm_item: str = find_best_match(_item, short_meta)
                        if sm_item:
                            sm_data_item = short_meta[sm_item]
                            # Return the item from the short_meta
                            return sm_data_item

    def version_compare(
        self,
        other_pyversion: str,
        item: str,
        *,
        opmethod: OperatorMethods = None,
    ) -> Optional[Any]:
        """
        This method can be used to compare the specified item for two different versions of the same package.

        #### Args:
            - `other_pyversion` (str): The Python version to compare the specified item.
            - `item` (str): The item to compare for the specified package.
            - `opmethod` (str): The operator method to use for comparison.
                - Possible Operator Methods (case-sensitive):
                    - `eq` or `==`: Equal to.
                    - `ne` or `!=`: Not equal to.
                    - `lt` or `<`: Less than.
                    - `le` or `<=`: Less than or equal to.
                    - `gt` or `>`: Greater than.
                    - `ge` or `>=`: Greater than or equal to.

        #### Returns:
            - `Any`: The result of the comparison between the two versions of the specified item.

        #### Raises:
            - `PkgException`:
                - If the Python version is not specified.
                - If the specified Python version is not found.
                - If the specified item is not found.
                - If the Python version matches the specified Python version for comparison.
                - If the specified item is not compatible for comparison.

        """
        self.__check_attrs()
        other_pyversion: PackageVersion = self._check_version(
            py_version=other_pyversion
        )

        if not item:
            # Raise an exception if the item is not specified
            raise PkgException(
                "A non-empty string-type item must be specified for comparison."
            )

        def _inspect(v):
            # Inspect the package for the specified Python version
            return PkgInspect(self._pkg, v, generator=False).inspect_package(item)

        # Retrieve the item for both versions of the package
        self_and_other = clone_gen(
            map(_inspect, (self._pyversion, other_pyversion)), iter_only=True
        )

        if self._pyversion == other_pyversion:
            raise PkgException(
                f"The Python version ({self._pyversion!r}) must not match the specified Python version ({other_pyversion = }) "
                "for comparison."
            )
        if op_handler := get_opmethod(opmethod, allow_none=True):
            # Check if the operator method is valid
            @base_exception_handler(
                msg=f"The specified item {item!r} is not compatible for comparison "
                f"with the specified operator method {opmethod!r}."
            )
            def op_item(_args):
                # Check if the item was found for both versions of the package
                if not any(none_args := next(_args)):
                    if not all(none_args):
                        failed_pyv = none_args
                    else:
                        failed_pyv = [self._pyversion, other_pyversion][
                            none_args[1] is None
                        ]
                    raise RedPkgE(
                        f"{item = } was not found for the following python versions:"
                        f"\n{failed_pyv = }."
                    )
                try:
                    # Return the comparison result between the two versions of the specified item
                    return op_handler(*next(_args))
                except:
                    # If fails, recursively call the method to compare the lengths of the two versions
                    # specified items
                    return op_item(*map(len, next(_args)))

            return op_item(self_and_other)
        # Otherwise, return the item for both versions of the package
        return (*next(self_and_other),)

    def get_site_package(self) -> Path:
        """
        Get the site package for the specified Python version and package name.

        #### Returns:
            - `Path`: The site package for the specified Python version and package name.

        #### Example:
        ```python
        >>> PkgInspect(package="pandas", pyversion="3.12").get_site_package()
        # Output:
        PosixPath('/usr/local/Cellar/python@3.12/3.12.2/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/')
        ```
        """
        # Check if the package/pyversion is specified
        self.__check_attrs()

        # Return the site package path for the specified package
        # Otherwise, will raise a 'PkgException' if the package is not found
        return self._get_site_package(self._pkg, self._pyversion)

    @generator_handler(is_string=True)
    def get_version_packages(self, **kwargs) -> list[str]:
        """
        Get the package names or the total number of packages for the specified Python version.

        #### Args:
            - `return_total` (bool): A boolean value indicating whether to return the total number of packages found.

        #### Returns:
            - `Union[list[str], int]`: The package names for the specified Python version.

        #### Raises:
            - `PkgException`: If no packages were found for the specified Python version.
        """
        return self._get_package_names(self._pyversion, **kwargs)

    @property
    def isinstalled_version(self) -> bool:
        """Check if the specified package is installed for the given Python version."""
        try:
            self._check_package(self._pyversion, self._pkg)
        except (*BASE_EXCEPTIONS, PkgException):
            return False
        return True

    @property
    def islatest_version(self) -> bool:
        """Return a boolean value indicating whether the package is the latest version."""
        return self.__pipv_pkg().is_latest(self.installed_version)

    @property
    @generator_handler(is_string=True)
    def available_updates(self) -> Optional[Iterator[PackageVersion]]:
        """Return the available updates for the specified package."""
        return self.__pipv_pkg().get_updates(self.installed_version)

    @property
    def installed_version(self) -> PackageVersion:
        """Return the installed version of the specified package."""
        return self._get_version_num(self.get_site_package(), dist_ver=True)

    @cached_property
    @generator_handler(is_string=True)
    def get_fieldnames(self) -> tuple[str]:
        """Return the available fieldnames for inspection."""
        return self.inspect_package()


# endregion
