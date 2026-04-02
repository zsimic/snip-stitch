#!/usr/bin/env python3

"""
Add a snippet to a bash/zsh/... shell rc file
"""

import argparse
import os
import sys

DRYRUN = False


class Defaults:
    comment_chars = "#"
    snip_marker = "-8<-"
    start_comment = "managed section, avoid editing"
    end_comment = ""


class ShellRc:
    def __init__(self, tag, target_path, snippet_contents, verbose=False):
        """
        Args:
            tag (str): Tag identifying the section
            target_path (str): Target file to modify (ex: ~/.bash_profile)
            snippet_contents (str): Example: "file:some-path" or "<some inlined content>"
            verbose (bool): If True, show all chatter on stderr
        """
        # All arguments are processed in some way, keep originally given values for logging and error reporting purposes
        self.tag = tag
        self.given_target_path = target_path
        self.given_snippet_contents = snippet_contents
        self.verbose = verbose
        self.target_path = os.path.expanduser(target_path)
        self.comment_chars = Defaults.comment_chars
        self.snip_marker = Defaults.snip_marker
        self.start_comment = Defaults.start_comment
        self.end_comment = Defaults.end_comment
        self.before_insertion = []
        self.marked_contents = []
        self.after_insertion = []
        self.target_contents = self.file_contents(self.target_path)
        self.snippet_contents = self.resolved_snippet_contents(snippet_contents)

    def debug(self, message):
        if self.verbose:
            self.inform(message)

    def inform(self, message):
        """
        Args:
            message (str): Message to log on stderr
        """
        print(message, file=sys.stderr)

    def validate_comment(self, comment, option_name):
        if comment:
            comment = self.splitlines(comment)
            if len(comment) > 1:
                line_count = len(comment)
                comment = "\n".join(comment)
                sys.exit(f"Provide maximum one line for --{option_name}, got %s lines:\n%s" % (line_count, comment))

    def resolved_snippet_contents(self, snippet_contents):
        """
        Args:
            snippet_contents (str): Snippet to add, can be a "file:...", or "_empty_", or actual content

        Returns:
            (list[str]): Actual snippet contents
        """
        if not snippet_contents or snippet_contents == "_empty_":
            # "_empty_" can be used as a placeholder for asking to remove added snippet
            return []

        if snippet_contents.startswith("file:"):
            # Grab contents of stated file:
            return self.file_contents(snippet_contents[5:])

        if "\\n" in snippet_contents:
            snippet_contents = snippet_contents.replace("\\n", "\n")

        return self.splitlines(snippet_contents)

    @staticmethod
    def splitlines(text):
        """
        Args:
            text (str | list | None): Text to split

        Returns:
            (list): Meaningful/groomed lines from 'text'
        """
        return text.strip().splitlines() if text else []

    def file_contents(self, path):
        """
        Args:
            path (str): Path to file

        Returns:
            (list[str]): Contents of the file (list of lines)
        """
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return []

        with open(path) as fh:
            return self.splitlines(fh.read())

    @property
    def marker_start(self):
        return f"{self.comment_chars} --{self.snip_marker} {self.tag} --"

    @property
    def marker_end(self):
        return f"{self.comment_chars} {self.snip_marker}-- {self.tag} --"

    def parse_target_contents(self):
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

    def rendered_snippet(self, include_marker=True):
        """
        Args:
            include_marker (bool): Used for testing

        Returns:
            (list[str]): Rendered snippet, optionally with the section marker
        """
        self.validate_comment(self.start_comment, "start-comment")
        self.validate_comment(self.end_comment, "end-comment")
        result = []
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

    def rendered_target_contents(self):
        """
        Returns:
            (str): Rendered contents of target file (with snippet + its marker included)
        """
        result = []
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

    def write_content(self, target_path, contents):
        """
        Args:
            target_path (str): Path to target file, example: ~/.bash_profile
            contents (str): Contents to write to the file
        """
        self.inform("Updating %s" % target_path)
        self.debug("Contents:\n%s" % contents)
        with open(target_path, "w") as fh:
            fh.write(contents)
            if contents and contents[-1] != "\n":
                fh.write("\n")

    def run_update(self, force=False):
        """
        Perform the actual update: inject snippet into the target file, in an idempotent manner

        Args:
            force (bool): If True, regenerate contents even if they didn't change
        """
        self.parse_target_contents()
        snippet_contents = self.rendered_snippet(include_marker=False)
        if not force and snippet_contents == self.marked_contents:
            self.inform("Section has not changed, not modifying '%s'" % self.given_target_path)
            return

        rendered_contents = self.rendered_target_contents()
        if DRYRUN:
            self.inform("[DRYRUN] Would update %s, contents:" % self.given_target_path)
            self.inform(rendered_contents)
            return

        # Write updated contents
        self.write_content(self.target_path, rendered_contents)


def main():
    parser = argparse.ArgumentParser(prog="snip-stitch", description=__doc__)
    parser.add_argument("--dryrun", "-n", action="store_true", help="Perform a dryrun")
    parser.add_argument("--verbose", "-v", action="store_true", help="Be verbose")
    parser.add_argument("--force", "-f", action="store_true", help="Force update, even if not needed")
    parser.add_argument("--comment-chars", default=Defaults.comment_chars, help="Character(s) that constitute a comment in target file")
    parser.add_argument("--start-comment", default=Defaults.start_comment, help="Optional comment when opening the section")
    parser.add_argument("--end-comment", default=Defaults.end_comment, help="Optional comment when ending the section")
    parser.add_argument("--snip-marker", default=Defaults.snip_marker, help="Snip marker to use (default: '%(default)s)'")
    parser.add_argument("tag", help="Tag for identification")
    parser.add_argument("target_path", help="Path to file to modify (ex: ~/.bash_profile)")
    parser.add_argument("snippet", help="Snippet to add to target file, or file:<path> (use contents of referred file:)")
    args = parser.parse_args()

    global DRYRUN
    DRYRUN = args.dryrun

    shell_rc = ShellRc(args.tag, args.target_path, args.snippet, verbose=args.verbose)
    shell_rc.comment_chars = args.comment_chars
    shell_rc.snip_marker = args.snip_marker
    shell_rc.start_comment = args.start_comment
    shell_rc.end_comment = args.end_comment
    return shell_rc.run_update(force=args.force)


if __name__ == "__main__":  # pragma: no covers
    sys.exit(main())
