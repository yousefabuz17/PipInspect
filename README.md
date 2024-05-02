<img src="logo/pkginspect_logo.png" alt="PkgInspect Logo" width=250>

# Python Package Inspector

This module is designed to inspect and compare Python packages and Python versions. It provides a set of tools and utility classes to help retrieve information from installed Python packages, compare versions, and extract various details about Python installations.

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Dependencies](#dependencies)
- [Main-Components](#main-components)
    - [Core-Modules](#core-modules)
    - [Functions](#functions)
- [Inspection Field Options](#inspection-field-options)
- [Feedback](#feedback)
    - [Contact Information](#contact-information)

## Overview
This module offers comprehensive tools to inspect Python packages and Python installations. It allows you to retrieve package information, compare different Python versions, and extract details from installed packages.

## Key Features
- **Inspect Packages**: Retrieve information about installed Python packages.
- **Compare Versions**: Compare package data across different Python versions.
- **Retrieve Installed Pythons**: Identify and list installed Python versions.
- **Inspect PyPI Packages**: Retrieve information about packages from the Python Package Index (PyPI).
- **Fetch Available Updates**: Fetch available updates for a package from the current version.
- **List Inspection Fieldnames**: Access a list of available fieldnames for inspection.
- **Retrieve Package Metrics**: Extract OS statistics about a package.
- **Fetch GitHub Statistics**: Retrieve statistics about a package from GitHub.
- **Retrieve all Python Packages**: List all installed Python packages for a given Python version.

---

## Dependencies
- `aiohttp`
- `beautifulsoup4`
- `importlib_metadata`
- `packaging`
- `pypistats`
- `rapidfuzz`

---

## Main Components
### Core Modules
- `PkgInspect`: Inspects Python packages and retrieves package information.
- `PkgVersions`: Retrieves and compares package data across different Python versions.
- `PkgMetrics`: Extracts OS statistics about a package.

### Functions
- `inspect_package`: Inspects a Python package and retrieves package information.
- `inspect_pypi`: Inspects a package from the Python Package Index (PyPI).
- `get_available_updates`: Fetches available updates for a package from the current version.
- `get_installed_pythons`: Identifies and lists installed Python versions.
- `get_version_packages`: Lists all installed Python packages for a given Python version.
- `pkg_version_compare`: Compares package data across different Python versions.
---


## Inspection Field Options
The `PkgInspect` class provides a list of fieldnames that can be used to inspect Python packages. These fieldnames can be used to retrieve specific information about a package.
>>**Any other field name will be treated as a file name to inspect from the packages' site-path directory.**

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

- `pypistats fields`: Possible Fields from the `pypistats` module.
    - `all-pypi-stats` (dict[str, Any]): Returns all the statistics of the package on PyPI into a single dictionary.
    - `stats-overall` (dict[str, Any]): Returns the overall statistics of the package on PyPI.
    - `stats-major` (dict[str, Any]): Returns the major version statistics of the package on PyPI.
    - `stats-minor` (dict[str, Any]): Returns the minor version statistics of the package on PyPI.
    - `stats-recent` (dict[str, Any]): Returns the recent statistics of the package on PyPI.
    - `stats-system` (dict[str, Any]): Returns the system statistics of the package on PyPI.

---

# Feedback

Feedback is crucial for the improvement of the `PkgInspect` project. If you encounter any issues, have suggestions, or want to share your experience, please consider the following channels:

1. **GitHub Issues**: Open an issue on the [GitHub repository](https://github.com/yousefabuz17/PkgInspect) to report bugs or suggest enhancements.

2. **Contact**: Reach out to the project maintainer via the following:

### Contact Information
- [Discord](https://discord.com/users/581590351165259793)
- [Gmail](yousefzahrieh17@gmail.com)

## License:

This project is licensed under the Apache 2.0 license. See the [LICENSE.md](LICENSE.md) file for details.