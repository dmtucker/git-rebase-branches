#!/usr/bin/env python3


"""Rebase branches in batch."""


import argparse

import shlex
import subprocess
import sys
from contextlib import contextmanager
from importlib.metadata import version
from typing import Any, Iterator, Optional


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
        "--version",
        action="version",
        version=f"%(prog)s {version(__name__)}",
    )
    parser.add_argument("base_ref", type=valid_git_ref, help="the ref to rebase on")
    return parser


def branches_that_do_not_contain(ref: str, /) -> list[str]:
    """Get a list of branches that do not contain a given ref."""
    result = run(
        ["git", "branch", "--no-contains", ref, "--format=%(refname:short)"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    print(result.stdout, end="", flush=True)
    return result.stdout.splitlines()


def stash_changes() -> bool:
    """Stash any local changes, and return whether changes were stashed."""
    result = subprocess.run(
        ["git", "stash", "list"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    stashed_changes = len(result.stdout.splitlines())
    run(["git", "stash", "push", "--include-untracked"], check=True)
    result = subprocess.run(
        ["git", "stash", "list"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return bool(len(result.stdout.splitlines()) - stashed_changes)


@contextmanager
def changes_stashed() -> Iterator[bool]:
    """Stash any local changes, then un-stash them."""
    stashed_changes = stash_changes()
    try:
        yield stashed_changes
    finally:
        if stashed_changes:
            run(["git", "stash", "pop"], check=True)


def ref_commit(ref: str, /) -> str:
    """Get the commit for a given ref."""
    result = subprocess.run(
        ["git", "rev-parse", ref],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def current_ref() -> str:
    """Get the current Git branch, commit, etc."""
    run(["git", "log", "-n1"], check=True)
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return result.stdout.strip() or ref_commit("HEAD")


@contextmanager
def original_ref_preserved() -> Iterator[str]:
    """Note the current ref, then restore it."""
    og_ref = current_ref()
    try:
        yield og_ref
    finally:
        run(["git", "-c", "advice.detachedHead=false", "checkout", og_ref], check=True)


@contextmanager
def original_state_preserved() -> Iterator[tuple[bool, str]]:
    """Stash any local changes and note the current ref, then restore both."""
    with changes_stashed() as stashed_changes:
        with original_ref_preserved() as og_ref:
            yield stashed_changes, og_ref


def main(argv: Optional[list[str]] = None) -> None:
    """Execute CLI commands."""
    if argv is None:
        argv = sys.argv[1:]
    args = cli().parse_args(argv)
    if args.branches is None:
        args.branches = branches_that_do_not_contain(args.base_ref)

    statuses: dict[str, str] = {}

    # Rebase each branch.
    with original_state_preserved():
        for branch in args.branches:
            try:
                run(["git", "rebase", args.base_ref, branch], check=True)
            except subprocess.CalledProcessError:
                statuses[branch] = FAILURE_STATUS
                run(["git", "rebase", "--abort"], check=True)
            else:
                statuses[branch] = "succeeded"

    # Report what happened.
    for i, branch in enumerate(args.branches):
        if i == 0:
            print()
            print("=" * 36, "SUMMARY", "=" * 36)
        print("-", branch, f"({statuses[branch]})")

    sys.exit(FAILURE_STATUS in statuses.values())


def run(command: list[str], **kwargs: Any) -> "subprocess.CompletedProcess[str]":
    """Print a command before running it."""
    print("$", shlex.join(str(token) for token in command), flush=True)
    return subprocess.run(command, check=kwargs.pop("check", True), **kwargs)


if __name__ == "__main__":
    main()
