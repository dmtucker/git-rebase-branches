# git-rebase-branches

Rebase multiple branches at once.

***

Say I have a number of feature branches, and new commits are added to `main`:

``` console
dmtucker@localhost:/tmp/tmp.97ZHC4YUiK $ git branch -vv
  feature1 2511789 Add feature #1
  feature2 339ff60 Make fizz do buzz
* feature3 618d195 Improve thing greatly
  main     77bf560 New commits to main!
```

My feature branches are no longer based on `main` and all need to be rebased:

``` console
dmtucker@localhost:/tmp/tmp.97ZHC4YUiK $ git log --graph feature1 feature2 feature3 main
* 618d195 (HEAD -> feature3) Improve thing greatly
| * 339ff60 (feature2) Make fizz do buzz
|/
| * 2511789 (feature1) Add feature #1
|/
| * 77bf560 (main) New commits to main!
|/
* cd9b6c6 Initial commit
```

`git-rebase-branches` can help with that:

``` console
dmtucker@localhost:/tmp/tmp.97ZHC4YUiK $ git-rebase-branches main
$ git for-each-ref --no-contains main '--format=%(refname:short)' refs/heads/
feature1
feature2
feature3
$ git stash push --include-untracked
No local changes to save
$ git log -n1
618d195 (HEAD -> feature3) Improve thing greatly
$ git rebase main feature1
Successfully rebased and updated refs/heads/feature1.
$ git rebase main feature2
Successfully rebased and updated refs/heads/feature2.
$ git rebase main feature3
Successfully rebased and updated refs/heads/feature3.
$ git -c advice.detachedHead=false checkout feature3
Already on 'feature3'

==================================== SUMMARY ====================================
- feature1 (succeeded)
- feature2 (succeeded)
- feature3 (succeeded)
```
- Note: Once you run the first command, `git-rebase-branches` prints and runs the rest.

Now, all feature branches are based on `main`:

``` console
dmtucker@localhost:/tmp/tmp.97ZHC4YUiK $ git log --graph feature1 feature2 feature3 main
* 069fcca (HEAD -> feature3) Improve thing greatly
| * e32b491 (feature1) Add feature #1
|/
| * 8fffd21 (feature2) Make fizz do buzz
|/
* 77bf560 (main) New commits to main!
* cd9b6c6 Initial commit
```
