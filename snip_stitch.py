#!/usr/bin/env python3

"""
Add a snippet to a bash/zsh/... shell rc file
"""

from __future__ import annotations

import argparse
import os
import re
import sys

DRYRUN = False
VERBOSE = False


def inform(message: str) -> None:
    print(message, file=sys.stderr)


def debug(message: str) -> None:
    if VERBOSE:
        inform(message)


def splitlines(text: str | None) -> list[str]:
    return text.strip().splitlines() if text else []


class Defaults:
    comment_chars = "#"
    snip_marker = "-8<-"
    start_comment = "managed section, avoid editing"
    end_comment = ""


class SnipStitch:
    def __init__(self, tag: str, target_path: str, snippet_lines: list[str]) -> None:
        self.tag = tag
        self.given_target_path = target_path
        self.target_path = os.path.expanduser(target_path)
        self.comment_chars = Defaults.comment_chars
        self.snip_marker = Defaults.snip_marker
        self.start_comment = Defaults.start_comment
        self.end_comment = Defaults.end_comment
        self.before_insertion: list[str] = []
        self.marked_contents: list[str] = []
        self.after_insertion: list[str] = []
        self.target_contents = self.read_file(self.target_path)
        self.snippet_contents = snippet_lines

    @staticmethod
    def read_file(path: str) -> list[str]:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return []

        with open(path) as fh:
            return splitlines(fh.read())

    @property
    def marker_start(self) -> str:
        return f"{self.comment_chars} --{self.snip_marker} {self.tag} --"

    @property
    def marker_end(self) -> str:
        return f"{self.comment_chars} {self.snip_marker}-- {self.tag} --"

    def parse_target_contents(self) -> None:
        """Parse existing target file, recognize any already-existing section"""
        self.before_insertion = []
        self.marked_contents = []
        self.after_insertion = []
        accumulator = self.before_insertion
        marker_start = self.marker_start
        marker_end = self.marker_end
        for line in self.target_contents:
            if accumulator is self.after_insertion:
                accumulator.append(line)
                continue

            if line.startswith(marker_start):
                accumulator = self.marked_contents
                continue

            if line.startswith(marker_end):
                accumulator = self.after_insertion
                continue

            accumulator.append(line)

    def rendered_snippet(self, include_marker: bool = True) -> list[str]:
        result: list[str] = []
        if self.snippet_contents:
            if include_marker:
                marker = self.marker_start
                if self.start_comment:
                    marker += f" {self.start_comment}"

                result.append(marker)

            result.extend(self.snippet_contents)
            if include_marker:
                marker = self.marker_end
                if self.end_comment:
                    marker += f" {self.end_comment}"

                result.append(marker)

        return result

    def rendered_target_contents(self) -> str:
        result: list[str] = []
        if self.before_insertion:
            result.extend(self.before_insertion)

        if self.snippet_contents and result and result[-1]:
            # Ensure an empty line is present before our insertion, for aeration
            result.append("")

        result.extend(self.rendered_snippet(include_marker=True))
        if self.after_insertion:
            if result and result[-1] and self.after_insertion and self.after_insertion[0]:
                # Ensure an empty line is present after our insertion, for aeration
                result.append("")

            result.extend(self.after_insertion)

        return "\n".join(result)

    def write_content(self, target_path: str, contents: str) -> None:
        inform(f"Updating {target_path}")
        debug(f"Contents:\n{contents}")
        with open(target_path, "w") as fh:
            fh.write(contents)
            if contents and contents[-1] != "\n":
                fh.write("\n")

    def run_update(self, force: bool = False) -> None:
        self.parse_target_contents()
        snippet_contents = self.rendered_snippet(include_marker=False)
        if not force and snippet_contents == self.marked_contents:
            inform(f"Section has not changed, not modifying '{self.given_target_path}'")
            return

        rendered_contents = self.rendered_target_contents()
        if DRYRUN:
            inform(f"[DRYRUN] Would update {self.given_target_path}, contents:")
            inform(rendered_contents)
            return

        # Write updated contents
        self.write_content(self.target_path, rendered_contents)


TAG_RE = re.compile(r"[a-z][a-z0-9._-]{2,31}$")


def validated_tag(value: str) -> str:
    """argparse type function: validate tag format"""
    if not TAG_RE.match(value):
        raise argparse.ArgumentTypeError(f"invalid tag '{value}' (must be 3-32 lowercase chars, matching [a-z][a-z0-9._-]{{2,31}})")
    return value


def validated_comment(value: str) -> str:
    """argparse type function: validate comment (single line, max 120 chars)"""
    if "\n" in value:
        lines = splitlines(value)
        if len(lines) > 1:
            raise argparse.ArgumentTypeError(f"comment must be a single line, got {len(lines)} lines")

    if len(value) > 120:
        raise argparse.ArgumentTypeError(f"comment too long ({len(value)} chars, max 120)")

    return value


def resolved_text(text: str) -> list[str]:
    """Resolve inline text: expand \\n escapes and split into lines"""
    if "\\n" in text:
        text = text.replace("\\n", "\n")

    return splitlines(text)


def main():
    parser = argparse.ArgumentParser(prog="snip-stitch", description=__doc__)
    parser.add_argument("--dryrun", "-n", action="store_true", help="Perform a dryrun")
    parser.add_argument("--verbose", "-v", action="store_true", help="Be verbose")
    parser.add_argument("--force", "-f", action="store_true", help="Force update, even if not needed")
    parser.add_argument("--comment-chars", default=Defaults.comment_chars, help="Character(s) that constitute a comment in target file")
    parser.add_argument("--start-comment", type=validated_comment, default=Defaults.start_comment, help="Comment when opening the section")
    parser.add_argument("--end-comment", type=validated_comment, default=Defaults.end_comment, help="Comment when ending the section")
    parser.add_argument("--snip-marker", default=Defaults.snip_marker, help="Snip marker to use (default: '%(default)s)'")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    text_parser = subparsers.add_parser("text", help="Use inline text as snippet content")
    text_parser.add_argument("tag", type=validated_tag, help="Tag for identification")
    text_parser.add_argument("target", help="Path to file to modify (ex: ~/.bash_profile)")
    text_parser.add_argument("content", help="Snippet text to add")

    file_parser = subparsers.add_parser("file", help="Use contents of a file as snippet")
    file_parser.add_argument("tag", type=validated_tag, help="Tag for identification")
    file_parser.add_argument("target", help="Path to file to modify (ex: ~/.bash_profile)")
    file_parser.add_argument("source", help="Path to file whose contents will be used as the snippet")

    remove_parser = subparsers.add_parser("remove", help="Remove a managed section")
    remove_parser.add_argument("tag", type=validated_tag, help="Tag for identification")
    remove_parser.add_argument("target", help="Path to file to modify (ex: ~/.bash_profile)")

    args = parser.parse_args()

    global DRYRUN, VERBOSE
    DRYRUN = args.dryrun
    VERBOSE = args.verbose

    if args.command == "text":
        snippet_lines = resolved_text(args.content)
    elif args.command == "file":
        snippet_lines = SnipStitch.read_file(args.source)
    else:
        snippet_lines = []

    ss = SnipStitch(args.tag, args.target, snippet_lines)
    ss.comment_chars = args.comment_chars
    ss.snip_marker = args.snip_marker
    ss.start_comment = args.start_comment
    ss.end_comment = args.end_comment
    ss.run_update(force=args.force)


if __name__ == "__main__":  # pragma: no covers
    sys.exit(main())
