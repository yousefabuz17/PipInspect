from __future__ import annotations

from .pkg_inspect import *


__version__: PackageVersion = PkgVersions.parse_version("0.1.6")


if __name__ == "__main__":
    print(cli_parser(__version__))