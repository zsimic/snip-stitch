# bookend-my-snippet

Idempotently add, update, or remove managed snippets inside shell-like text files.
Snip-stitch managed blocks into config files

Example:
```shell
#- ---8<- nvm-installer -- managed section, avoid editing
if [ -z "${NVM_DIR:-}" ]; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
fi
#- -8<--- nvm-installer --

#- ---8<- brew -- managed section, avoid editing
eval "$(brew shellenv)"
#- -8<--- brew --
```

Marker structure:
```
{empty_line_if_needed}
{comment_chars} --{snip_marker} {tag} -- {start_comment}
...
{comment_chars} {snip_marker}-- {tag} -- {end_comment}
{empty_line_if_needed}
```

Defaults (`tag` has no default, must be provided):
```
comment_chars = "#-"
snip_marker = "-8<-"
start_comment = "managed section, avoid editing"
end_comment = ""
```

`tag` must be mostly alphanumeric, minimum 3 chars, max 32:
```regexp
[a-z][a-z0-9._-]{2,31}
```

`bookend-my-snippet` is a tiny CLI for installers, dotfiles, and automation that need to own a
small section of a file without clobbering the rest of it.

Think:

- shell installers that currently do `grep ... || echo ... >> ~/.zshrc`
- dotfiles that need to manage one section of `~/.bashrc`, `~/.zprofile`, or `~/.ssh/config`
- setup automation that wants predictable, testable behavior instead of ad-hoc shell glue

The tool wraps the snippet it owns with marker lines, so future runs can update or remove exactly
that section and leave everything else alone.

> Idem-potent by design.

# Motivation

Appending lines blindly is easy to write and awkward to undo.

`bookend-my-snippet` aims to be the "do one thing well" tool for managed config snippets:

- idempotent updates
- explicit ownership through markers
- removal without brittle `sed`/`grep` gymnastics
- convenient snippet sources like file, raw text, or output of a command
- an intentionally small and testable surface area

## Examples

Use a file as the source of truth:

```bash
uvx bookend-my-snippet with-content ~/.bashrc sdkman-init.sh
```

Inject a one-liner snippet directly:

```bash
uvx bookend-my-snippet --tag rustup by-text ~/.profile \
  '[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"'
```

Evaluate a command and inject its stdout:

```bash
uvx bookend-my-snippet from-output ~/.zprofile brew-shellenv.zsh
```

Remove a section the tool previously managed:

```bash
uvx bookend-my-snippet --tag sdkman remove ~/.bashrc
```

## What It Manages

Given this command:

```bash
uvx bookend-my-snippet --tag nvm ~/.zshrc file:nvm-profile.zsh
```

The file will end up containing a block like this:

```text
## -- Added by nvm -- DO NOT MODIFY THIS SECTION
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
## -- end of addition by nvm --
```

If you run the same command again with different snippet contents but the same marker, the managed
section is updated in place.

## Supported Snippet Sources

- Inline text: pass the snippet directly as a positional argument
- `file:PATH`: read the snippet from a file
- `eval:COMMAND`: run a shell command and use its stdout as the snippet
- `--remove`: remove the managed section instead of adding or updating it

Inline snippets also support `\n` escapes, which is handy when a caller cannot easily pass a
literal multi-line argument.

## Behavior Guarantees

This project is intended to be boring in the best possible way:

- The same input should produce the same file contents.
- A marker owns exactly one managed section.
- Re-running with unchanged snippet contents should not rewrite the file.
- Removing a managed section should leave the surrounding file intact.
- The project should stay dependency-light and heavily tested.

## Command Line

```text
bookend-my-snippet [options] TARGET SOURCE
```

Key options:

- `-m`, `--marker`: marker to use (default: "# -bms- {tag}")
- `-t`, `--tag`: identifying tag within marker
- `--comment-marker`: comment marker for the targeted type of file (default: "#")
- `-c`, `--comment`: optional comment appended to the opening marker
- `-n`, `--dryrun`: show the would-be output without touching the file
- `-f`, `--force`: rewrite even if the managed section content is unchanged
- `--remove`: remove the managed section instead of adding or updating it
- `-v`, `--verbose`: print extra detail to stderr

## Installation

Intended for ad-hoc use (but can be used as a library too):

```bash
uvx bookend-my-snippet --help
```
