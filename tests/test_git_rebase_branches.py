"""Test git_rebase_branches."""


import pytest

import git_rebase_branches


def test_main_version():
    """Test --version."""
    with pytest.raises(SystemExit) as excinfo:
        git_rebase_branches.main(["--version"])
    assert excinfo.value.code == 0
