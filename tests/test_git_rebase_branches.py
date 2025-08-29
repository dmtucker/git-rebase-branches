"""Test git_rebase_branches."""

import subprocess

import pytest

import git_rebase_branches


def test_main_version():
    """Test --version."""
    with pytest.raises(SystemExit) as excinfo:
        git_rebase_branches.main(["--version"])
    assert excinfo.value.code == 0


def branch_commit():
    """Get a mapping of branches to commits."""
    result = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short) %(objectname)",
            "refs/heads",
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return {
        branch: commit
        for line in result.stdout.splitlines()
        for branch, _, commit in [line.partition(" ")]
    }


@pytest.mark.parametrize("detached", [False, True])
def test_git_rebase_branches(tmp_path, monkeypatch, detached):
    """Test a basic example."""
    base_ref = "main"
    branch_no_contains = "init"
    branch_contains = "latest"

    monkeypatch.chdir(tmp_path)
    commit_opts = ["--allow-empty"]
    commands = [
        ["init", "-b", base_ref],
        ["config", "commit.gpgsign", "false"],
        ["config", "user.name", "Coder Joe"],
        ["config", "user.email", "Coder@Joe.com"],
        ["commit"] + commit_opts + ["-m", "Initial Commit"],
        ["branch", branch_no_contains],
        ["commit"] + commit_opts + ["-m", "New Commit on main"],
        ["branch", branch_contains],
    ]
    if detached:
        commands.append(["switch", "-d", branch_no_contains])
    for git_command in commands:
        subprocess.run(["git"] + git_command, check=True)

    commit = git_rebase_branches.ref_commit(base_ref)
    target_state = {
        base_ref: commit,
        branch_no_contains: commit,
        branch_contains: commit,
    }
    assert branch_commit() != target_state

    with pytest.raises(SystemExit) as excinfo:
        git_rebase_branches.main([base_ref])
    assert excinfo.value.code == 0

    assert branch_commit() == target_state
