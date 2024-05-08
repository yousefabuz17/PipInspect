from .util_types import PackageVersion
from ..pkg_modules.pkg_versions import PkgVersions


# Current Version
__version__: PackageVersion = PkgVersions.parse_version("0.1.9")


# Package Metadata
__author__ = "Yousef Abuzahrieh <yousef.zahrieh17@gmail.com"
__copyright__ = f"Copyright © 2024, {__author__}"
__license__ = "Apache License, Version 2.0"
__summary__ = "A package for inspecting Python packages and their versions."
__url__ = "https://github.com/yousefabuz17/PkgInspect"


__all__ = (
    "__author__",
    "__copyright__",
    "__license__",
    "__summary__",
    "__url__",
    "__version__",
)
