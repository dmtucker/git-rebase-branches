#!/usr/bin/env python3


"""Rebase branches in batch."""


import argparse

try:
    from importlib.metadata import version
except ModuleNotFoundError:  # py37
    from importlib_metadata import version
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional


FAILURE_STATUS = "failed"


def valid_git_ref(token: str) -> str:
    """Raise an Exception if token is not a valid Git ref."""
    try:
        subprocess.run(
            ["git", "log", "-n1", token, "--"],
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        raise argparse.ArgumentTypeError(exc.stderr.rstrip()) from exc
    return token


def cli(parser: Optional[argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
    """Define CLI arguments and options."""
    if parser is None:
        parser = argparse.ArgumentParser()
    parser.add_argument(
        "--branches",
        type=valid_git_ref,
        nargs="+",
        help="the branches to rebase",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="exit instead of aborting a failed rebase",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version(__name__)}",
    )
    parser.add_argument("base_ref", type=valid_git_ref, help="the ref to rebase on")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Execute CLI commands."""
    if argv is None:
        argv = sys.argv[1:]
    args = cli().parse_args(argv)

    # Stash any changes.
    if (
        args.interactive
        and run(["git", "diff-index", "--exit-code", "HEAD", "--"]).returncode
    ):
        try:
            input(
                "\n"
                "There are local changes that need to be stashed or committed.\n"
                "Press ^C to stop here or Enter to stash them and continue.\n"
            )
        except KeyboardInterrupt:
            print()
            sys.exit(1)
    result = subprocess.run(
        ["git", "stash", "list"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    stashed_changes = len(result.stdout.splitlines())
    run(["git", "stash", "push"], check=True)
    result = subprocess.run(
        ["git", "stash", "list"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    stashed_changes = len(result.stdout.splitlines()) - stashed_changes

    # Note where we are so we can come back.
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    start = result.stdout.strip()
    if not start:
        result = subprocess.run(
            ["git", "show-ref", "--hash", "HEAD"],
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        start = result.stdout.strip()
    run(["git", "log", "-n1"], check=True)

    # Get all the branches that need rebasing.
    if args.branches is None:
        # Check out to the ref to ensure it won't show up in the next command.
        run(
            ["git", "-c", "advice.detachedHead=false", "checkout", args.base_ref],
            check=True,
        )
        result = run(
            ["git", "branch", "--no-contains", "HEAD", "--format=%(refname:short)"],
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        print(result.stdout, end="", flush=True)
        args.branches = result.stdout.splitlines()

    # Rebase each branch.
    statuses: Dict[str, str] = {}

    def print_report() -> int:
        failures = 0
        for i, branch in enumerate(sorted(args.branches)):
            if i == 0:
                print()
                print("=" * 36, "SUMMARY", "=" * 36)
            status = statuses.get(branch, "not attempted")
            if status == FAILURE_STATUS:
                failures += 1
            print("-", branch, f"({status})")

        if stashed_changes:
            print()
            run(["git", "stash", "list", f"-n{stashed_changes}"], check=True)

        return failures

    for branch in args.branches:
        run(["git", "switch", branch], check=True)
        try:
            run(["git", "rebase", args.base_ref], check=True)
        except subprocess.CalledProcessError:
            statuses[branch] = FAILURE_STATUS
            if args.interactive:
                try:
                    input("\nPress ^C to stop here or Enter to continue.\n")
                except KeyboardInterrupt:
                    print()
                    failures = print_report()
                    run(["git", "status"], check=True)
                    sys.exit(failures)
            run(["git", "rebase", "--abort"], check=True)
        else:
            statuses[branch] = "succeeded"

    # Return to the original state.
    run(["git", "-c", "advice.detachedHead=false", "checkout", start], check=True)
    if stashed_changes:
        run(["git", "stash", "pop"], check=True)
        stashed_changes -= 1

    # Report what happened.
    failures = print_report()
    sys.exit(failures)


def run(command: List[str], **kwargs: Any) -> "subprocess.CompletedProcess[str]":
    """Print a command before running it."""
    print("$", shlex.join(str(token) for token in command), flush=True)
    return subprocess.run(command, **kwargs)


if __name__ == "__main__":
    main()
