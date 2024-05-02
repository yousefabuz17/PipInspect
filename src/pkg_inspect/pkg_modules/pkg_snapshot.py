from .pkg_inspect import _PkgInspect
from ..pkg_utils import *


class PkgSnapshot:
    """
    A class for generating and exporting snapshots of Python environments using `pipinspect`.

    This class extends the functionality of the `PipInspect` class to provide the ability to generate
    and export snapshots of Python environments. It includes options for exporting various aspects of
    the environment, such as all information, package paths, package versions, Python versions, and site packages.

    ### Args:
        - `export_path` (Union[Path, str], optional): The path where the snapshot should be exported.
            Defaults to an empty string, indicating the current working directory.
        - `snap_option` (Literal["all", "package_paths", "package_versions", "pyversions", "site_packages"], optional):
            The specific aspect of the environment to include in the snapshot. Defaults to "all".

    ### Attributes:
        - `parent`: A private attribute representing the immediate base class (`PipInspect`) for internal use.
        - `snap_options`: A cached property containing valid snapshot options, including "all" and cached properties
            from the immediate base class.

    ### Methods:
        - `snapshot()`: Generates and exports the chosen snapshot based on the specified option.

    Example:
    ```python
    snapshot_instance = PkgSnapshot(export_path="/path/to/export", snap_option="package_paths")
    snapshot_instance.snapshot()
    ```

    In this example, a `PkgSnapshot` instance is created with the export path set to "/path/to/export" and
    the snapshot option set to "package_paths". The `snapshot()` method is then called to generate and export
    the snapshot.
    """

    __dict__ = {}
    __slots__ = ("__weakrefs__", "_export_p", "_option")

    parent: _PkgInspect = _PkgInspect

    def __init__(
        self,
        export_path: PathOrStr = "",
        snap_option: PyPIOptionsT = "",
    ) -> None:
        self._export_p = export_path
        self._option = snap_option

    @cached_property
    def snap_options(self) -> tuple[str, ...]:
        """
        Class properties containing valid snapshot options, including "all" and cached properties
        from the immediate base class.
        """
        return ("all", *get_properties(self.parent))

    def _validate_option(self) -> str:
        if self._option in self.snap_options:
            return self._option

        # Validate the chosen snapshot option against the available options
        option_msg = ""
        if possible_option := best_match(query=self._option, choices=self.snap_options):
            # If the option is not valid, suggest the best match.
            option_msg = f"Did you mean {possible_option!r}?"
        # Raise a `PipException` if option is not valid.
        raise PkgException(
            f"\n{self._option!r} is not a valid snapshot option." f"\n{option_msg!r}"
        )

    def snapshot(self):
        """
        Generate and export the chosen snapshot based on the specified option.
        """
        self._validate_option()
        # ep = self._validate_path(self._export_p)
        return getattr(self.parent(generator=False), self._option)
