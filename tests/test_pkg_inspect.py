import unittest

from src import *


class TestPkgInspect(unittest.TestCase):
    def test_inspect_package(self):
        # Create an instance of PipInspect
        pkg_inspect = PkgInspect(package="key_craftsman", pyversion="3.12")

        # Inspect the details of the 'pipinspect' package
        result = pkg_inspect.inspect_package(item="total_versions")

        # Assert that the result is a dictionary
        self.assertIsInstance(result, int)

    def test_check_package(self):
        # Create an instance of PipInspect
        pkg_inspect = PkgInspect()

        # Check the 'pipinspect' package for the specified Python version
        result = pkg_inspect._check_package(
            py_version="3.12", package_name="key_craftsman"
        )

        # Assert that the result is True
        self.assertTrue(result)

    def test_package_paths(self):
        # Create an instance of PipInspect
        pkg_inspect = PkgInspect()

        # Get the package paths for each Python version
        result = pkg_inspect.package_paths

        # Assert that the result is not empty
        self.assertIsNotNone(result)

    def test_package_versions(self):
        # Create an instance of PipInspect
        pkg_inspect = PkgInspect()

        # Get the package versions for each Python version
        result = pkg_inspect.package_versions

        # Assert that the result is not empty
        self.assertIsNotNone(result)

    def test_pyversions(self):
        # Create an instance of PipInspect
        pkg_inspect = PkgInspect()

        # Get the installed Python versions
        result = pkg_inspect.pyversions

        # Assert that the result is not empty
        self.assertIsNotNone(result)

    def test_site_packages(self):
        # Create an instance of PipInspect
        pkg_inspect = PkgInspect()

        # Get the site packages for each Python version
        result = pkg_inspect.site_packages

        # Assert that the result is not empty
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
