import os
import textwrap

import runez

ENSURE_PATH = """\
local_bin=~/.local/bin
if [[ $PATH != *"$local_bin"* && -d $1 ]]; then
    export PATH=$local_bin:$PATH
fi"""

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


EXPECTED_READD = """
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

    cli.run("text", "--help")
    assert cli.succeeded

    cli.run("remove", "--help")
    assert cli.succeeded


def test_dryrun(cli):
    # Snippet given as positional arg via 'text' subcommand
    cli.run("-n", "--end-comment", "peace", "text", "testing", "my-bash.rc", "some\ncontent")
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
    cli.run("-n", "--start-comment", "multiple\n\nlines", "text", "testing", "my-bash.rc", "some\ncontent")
    assert cli.failed
    assert "Provide maximum one line for --start-comment, got 3 lines:\nmultiple\n\nlines" in cli.logged.stderr.contents()


def test_samples(cli):
    sample_dir = os.path.join(runez.DEV.project_folder, "tests/samples")
    runez.copy(sample_dir, "samples", logger=None)

    # Dryrun remove: shows what would happen without modifying the file
    cli.run("-n", "remove", "my-test-app", "samples/bashrc")
    assert cli.succeeded
    lines = last_n_lines(5, cli.logged.stderr.contents())
    assert lines == [
        "[DRYRUN] Would update samples/bashrc, contents:",
        "# example bashrc file",
        "alias ls='ls -FGh'",
        "",
        "alias foo=~/bar",
    ]

    # Dryrun text with \n escapes
    cli.run("-n", "text", "my-test-app", "samples/bashrc", "foo\\nbar")
    assert cli.succeeded
    assert "[DRYRUN] Would update samples/bashrc" in cli.logged.stderr
    assert "foo\nbar\n# -8<--- my-test-app --" in cli.logged

    # Force update with text (same content as ensure-path sample)
    cli.run("-v", "--force", "text", "my-test-app", "samples/bashrc", ENSURE_PATH)
    assert cli.succeeded
    actual_lines = last_n_lines(13, cli.logged.stderr.contents())
    assert actual_lines == EXPECTED_REGEN.strip().splitlines()

    # Idempotent: same content again, no update
    cli.run("text", "my-test-app", "samples/bashrc", ENSURE_PATH)
    assert cli.succeeded
    assert "Section has not changed, not modifying 'samples/bashrc'" in cli.logged

    # Actually remove the section
    cli.run("remove", "my-test-app", "samples/bashrc")
    assert cli.succeeded
    assert "Updating samples/bashrc" in cli.logged.stderr.contents()
    contents = list(runez.readlines("samples/bashrc"))
    assert contents == ["# example bashrc file", "alias ls='ls -FGh'", "", "", "alias foo=~/bar"]

    # Re-add with text
    cli.run("text", "my-test-app", "samples/bashrc", ENSURE_PATH)
    assert cli.succeeded
    assert "Updating samples/bashrc" in cli.logged.stderr.contents()
    contents = "\n".join(runez.readlines("samples/bashrc"))
    assert contents == EXPECTED_READD.strip()
