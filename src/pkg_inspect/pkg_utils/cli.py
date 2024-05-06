from .utils import DUMMY_PATH, Any, PathOrStr, PackageVersion, CallableT, iread, partial
from ..pkg_functions.functions import (
    INSPECTION_FIELDS,
    get_available_updates,
    get_installed_pythons,
    get_version_packages,
    inspect_package,
    inspect_pypi,
    pkg_version_compare,
)

from argparse import ArgumentParser


def cli_parser(current_version: PackageVersion):
    """Command-line interface for 'pkg_inspect'."""
    
    # Functions for the CLI
    def _read(fp: PathOrStr) -> str:
        return iread(DUMMY_PATH / fp)

    def _store_true(func: CallableT, *args, **kwargs) -> partial[Any]:
        return partial(func, *args, action="store_true", **kwargs)
    
    
    # Default Argument Parser
    arg_parser = ArgumentParser(description="Command-line interface for 'pkg_inspect'")
    sub_parsers = arg_parser.add_subparsers(dest="command", help="All Command Options.")

    # Main Commands
    ap_true = _store_true(arg_parser.add_argument)
    ap_true("--doc", help="Display the README.md file.")
    ap_true("--license", help="Display the LICENSE.md file.")
    ap_true("--options", help="Display all possible inspections options.")
    ap_true("--req", help="Display the requirements.txt file.")
    ap_true("--source", help="Display the source code of 'pkg_inspect'.")
    ap_true("--version", help="Display the current version of 'pkg_inspect'.")
    ap_true("--installed-pythons", help="Display all installed python versions.")

    # Inspect Package
    i_package = sub_parsers.add_parser("inspect-package", help="Inspect a package.")
    ip_true = _store_true((ip_add := i_package.add_argument))
    ip_true("--ipdoc", help="Display the documentation of 'inspect_package'.")
    ip_add("-pkg", help="Choose a package to inspect.")
    ip_add("-pyver", help="Choose a python version to inspect.")
    ip_add("-item", help="Choose an 'itemOrfile' to inspect.")

    # Inspect PyPI
    ipypi = sub_parsers.add_parser("inspect-pypi", help="Inspect a package on PyPI.")
    ipypi_true = _store_true((ipypi_add := ipypi.add_argument))
    ipypi_true("--ipdoc", help="Display the documentation of 'inspect_pypi'.")
    ipypi_add("-pkg", help="Choose a package to inspect.")
    ipypi_add("-pyver", help="Choose a python version to inspect.")
    ipypi_add("-pkgm", help="Choose a package manager to inspect.")
    ipypi_add("-item", help="Choose an 'itemOrfile' to inspect.")

    # Retrieve Version Packages
    gvps = sub_parsers.add_parser("get-version-packages", help="Retrieve version packages.")
    gvps_true = _store_true((gvps_add := gvps.add_argument))
    gvps_true("--gvpdoc", help="Display the documentation of 'get_version_packages'.")
    gvps_add("-pyver", help="Choose a python version to inspect.")

    # Retrieve Available Updates
    gaup = sub_parsers.add_parser("get-available-updates", help="Retrieve available updates.")
    gaup_true = _store_true((gaup_add := gaup.add_argument))
    gaup_true("--gaupdoc", help="Display the documentation of 'get_available_updates'.")
    gaup_true("--include-betas", help="A flag to include beta versions.")
    gaup_add("-pkg", help="Choose a package to inspect.")
    gaup_add("-current-version", help="Choose a current version to inspect.")

    # Compare Version Packages
    pvc = sub_parsers.add_parser("pkg-version-compare", help="")
    pvc_true = _store_true((pvc_add := pvc.add_argument))
    pvc_true("--pvcdoc", help="Display the documentation of 'pkg_version_compare'.")
    pvc_add("-pkg", help="Choose a package to inspect.")
    pvc_add("-fpyver", help="Choose the first python version to inspect.")
    pvc_add("-opyver", help="Choose the second python version to inspect.")
    pvc_add("-item", help="Choose an 'itemOrfile' to inspect.")
    pvc_add("-opmethod", help="Choose an 'opmethod' to use.")

    # Parse Arguments
    args = arg_parser.parse_args()
    if args.doc:
        return _read("README.md")
    elif args.installed_pythons:
        return get_installed_pythons()
    elif args.license:
        return _read("LICENSE.md")
    elif args.options:
        return INSPECTION_FIELDS
    elif args.req:
        return _read("src/requirements.txt")
    elif args.source:
        return _read("src/pkg_inspect/pkg_modules/pkg_inspect.py")
    elif args.version:
        return current_version
    elif args.command == "inspect-package":
        if args.ipdoc:
            return inspect_package.__doc__
        return inspect_package(args.pkg, args.pyver, itemOrfile=args.item)
    elif args.command == "inspect-py":
        if args.pydoc:
            return inspect_pypi.__doc__
        return inspect_pypi(args.pkg, args.pkgm, item=args.item)
    elif args.command == "get-version-packages":
        if args.gvpdoc:
            return get_version_packages.__doc__
        return get_version_packages(args.pyver)
    elif args.command == "get-available-updates":
        if args.gaupdoc:
            return get_available_updates.__doc__
        return get_available_updates(
            args.pkg, args.current_version, include_betas=args.include_betas
        )
    elif args.command == "pkg-version-compare":
        if args.pvcdoc:
            return pkg_version_compare.__doc__
        return pkg_version_compare(
            args.pkg,
            args.fpyver,
            args.opyver,
            itemOrfile=args.item,
            opmethod=args.opmethod,
        )
