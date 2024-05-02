SRC_FILES := $(wildcard src/pkg_inspect/*.py)
MODULE_FILES := $(wildcard src/pkg_inspect/pkg_modules/*.py)
UTIL_FILES := $(wildcard src/pkg_inspect/pkg_utils/*.py)
FUNC_FILES := $(wildcard src/pkg_inspect/pkg_functions/*.py)
TEST_FILES := $(wildcard tests/*.py)

format:
	black $(SRC_FILES) $(MODULE_FILES) $(UTIL_FILES) $(FUNC_FILES) $(TEST_FILES)

black: format