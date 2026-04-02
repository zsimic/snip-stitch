from runez.conftest import cli, ClickRunner  # noqa: F401, fixture

from snip_stitch import main

ClickRunner.default_main = main
