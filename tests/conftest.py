from runez.conftest import cli, ClickRunner  # noqa: F401, fixture

from bookend_my_snippet.__main__ import main

ClickRunner.default_main = main
