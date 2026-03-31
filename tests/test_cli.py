import os
import textwrap

import runez

EXPECTED_REGEN = """
Updating samples/bashrc
Contents:
# example bashrc file
alias ls='ls -FGh'

# ---8<- my-test-app -- managed section, avoid editing
local_bin=~/.local/bin
if [[ $PATH != *"$local_bin"* && -d $1 ]]; then
    export PATH=$local_bin:$PATH
fi
# -8<--- my-test-app --

alias foo=~/bar
"""


EXPECTED_EMPTIED_REGEN = """
# example bashrc file
alias ls='ls -FGh'


alias foo=~/bar

# ---8<- my-test-app -- managed section, avoid editing
local_bin=~/.local/bin
if [[ $PATH != *"$local_bin"* && -d $1 ]]; then
    export PATH=$local_bin:$PATH
fi
# -8<--- my-test-app --
"""


def last_n_lines(n, text):
    return text.splitlines()[-n:]


def test_cli(cli):
    cli.run("--help")
    assert cli.succeeded
    assert "usage:" in cli.logged.stdout


def test_dryrun(cli):
    # Snippet given as positional arg
    cli.run("-n", "testing", "my-bash.rc", "some\ncontent", "--end-comment", "peace")
    assert cli.succeeded
    expected = textwrap.dedent("""\
        [DRYRUN] Would update my-bash.rc, contents:
        # ---8<- testing -- managed section, avoid editing
        some
        content
        # -8<--- testing -- peace
    """)
    assert cli.logged.stderr.contents() == expected

    # Multi-line comment is not accepted
    cli.run("-n", "testing", "my-bash.rc", "some\ncontent", "--start-comment", "multiple\n\nlines")
    assert cli.failed
    assert "Provide maximum one line for --start-comment, got 3 lines:\nmultiple\n\nlines" in cli.logged.stderr.contents()


def test_samples(cli):
    sample_dir = os.path.join(runez.DEV.project_folder, "tests/samples")
    runez.copy(sample_dir, "samples", logger=None)

    cli.run("-v", "my-test-app", "samples/bashrc", "file:samples/ensure-path")
    assert cli.succeeded
    assert "Section has not changed, not modifying 'samples/bashrc'" in cli.logged.stderr.contents()

    cli.run("-n", "my-test-app", "samples/bashrc", "_empty_")
    assert cli.succeeded
    lines = last_n_lines(5, cli.logged.stderr.contents())
    assert lines == [
        "[DRYRUN] Would update samples/bashrc, contents:",
        "# example bashrc file",
        "alias ls='ls -FGh'",
        "",
        "alias foo=~/bar",
    ]
    assert "[DRYRUN] Would update samples/bashrc" in cli.logged.stderr
    assert "## -- Added by my-test-app" not in cli.logged

    cli.run("-n", "my-test-app", "samples/bashrc", "foo\\nbar")
    assert cli.succeeded
    assert "[DRYRUN] Would update samples/bashrc" in cli.logged.stderr
    assert "foo\nbar\n# -8<--- my-test-app --" in cli.logged

    cli.run("-v", "--force", "my-test-app", "samples/bashrc", "file:samples/ensure-path")
    assert cli.succeeded
    actual_lines = last_n_lines(13, cli.logged.stderr.contents())
    assert actual_lines == EXPECTED_REGEN.strip().splitlines()

    cli.run("my-test-app", "samples/bashrc", "file:samples/ensure-path")
    assert cli.succeeded
    assert "Section has not changed, not modifying 'samples/bashrc'" in cli.logged

    cli.run("my-test-app", "samples/bashrc", "_empty_")
    assert cli.succeeded
    assert "Updating samples/bashrc" in cli.logged.stderr.contents()
    contents = list(runez.readlines("samples/bashrc"))
    assert contents == ["# example bashrc file", "alias ls='ls -FGh'", "", "", "alias foo=~/bar"]

    cli.run("my-test-app", "samples/bashrc", "file:samples/ensure-path")
    assert cli.succeeded
    assert "Updating samples/bashrc" in cli.logged.stderr.contents()
    contents = runez.readlines("samples/bashrc")
    contents = "\n".join(contents)
    assert contents == EXPECTED_EMPTIED_REGEN.strip()
