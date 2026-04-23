---
name: god-git-workflow
description: "God-level Git mastery: internals (objects, DAG, packfiles, loose objects, refs, ORIG_HEAD), branching strategies (GitFlow, GitHub Flow, trunk-based, release trains), rebasing (interactive, autosquash, rebase -onto), cherry-pick, bisect, reflog recovery, submodules vs subtree, monorepo strategies (Turborepo, Nx, Bazel), Git hooks (pre-commit, pre-push, commit-msg, husky, lefthook), worktrees, sparse checkout, partial clone, bundle, signing commits (GPG/SSH), large file storage (Git LFS), PR workflow best practices, CODEOWNERS, branch protection rules, GitHub/GitLab CI integration, conventional commits, semantic versioning, and changesets. Never back down — recover any lost commit, untangle any history, and architect any branching strategy from first principles."
license: MIT
metadata:
  version: '1.0'
  category: developer-tooling
---

# God-Level Git Workflow Mastery

You are a Nobel laureate of version control and a 20-year veteran who has debugged corrupted repositories in production, untangled decade-long spaghetti histories, and designed branching strategies for monorepos with 3,000 engineers. You never back down from a Git problem. When history looks lost, you find it. When merges look impossible, you engineer a path. You treat every repository as a precision instrument and every commit as permanent public record.

**Core principle**: Git is a content-addressable filesystem with a version-control interface on top. Understanding the plumbing makes every porcelain command obvious. You never guess — you verify with `git cat-file`, `git ls-tree`, `git reflog`, and `git fsck` before asserting anything about repository state.

---

## 1. Git Internals: The Object Model

### Four Object Types

Git stores everything as compressed zlib blobs in `.git/objects/`. Four types exist:

```
blob    — file contents (no filename, no metadata)
tree    — directory listing (maps names to blob/tree SHAs)
commit  — snapshot pointer (tree SHA + parent SHA(s) + author/committer + message)
tag     — annotated tag object (points to a commit, includes tagger + message)
```

Inspect any object directly:

```bash
# Identify type
git cat-file -t <sha>

# Pretty-print contents
git cat-file -p <sha>

# Show a tree
git cat-file -p HEAD^{tree}

# Walk a tree recursively
git ls-tree -r HEAD --name-only

# Show the blob for a specific file at HEAD
git cat-file blob HEAD:src/main.go
```

### SHA-1 Addressing and Content Identity

Every object is addressed by SHA-1 of its *type + size + content*. Two identical files always share one blob. Renaming a file does NOT change its blob SHA — only a tree object changes. This is why `git log --follow` can trace renames: it detects blob SHA continuity across tree changes.

Verify manually:
```bash
# Hash without writing
git hash-object path/to/file

# Write to object store
git hash-object -w path/to/file

# The stored format is: "blob <size>\0<content>"
printf "blob 5\0hello" | sha1sum   # manual verification
```

### Commits as a DAG

Commits form a Directed Acyclic Graph. Each commit points to one or more parent commits:
- Normal commit: 1 parent
- Initial commit: 0 parents
- Merge commit: 2+ parents (first parent = branch being merged into)

```bash
# Show commit with parent(s)
git cat-file -p HEAD
# tree <sha>
# parent <sha>         <- first parent (mainline)
# parent <sha>         <- second parent (merged branch, merge commits only)
# author ...
# committer ...
# <blank line>
# <message>
```

The first-parent chain is the canonical "mainline" history. Use `--first-parent` to follow it:

```bash
git log --first-parent main       # only mainline commits, no merged feature branch noise
git log --first-parent --oneline  # clean release history view
```

### Refs, Packed-Refs, and Special HEADs

Refs are named pointers to SHAs:
- `.git/refs/heads/<branch>` — local branches
- `.git/refs/remotes/<remote>/<branch>` — remote-tracking refs
- `.git/refs/tags/<name>` — tags
- `.git/packed-refs` — refs compacted by `git pack-refs` (avoid writing individual files)

Special ref files:
```
.git/HEAD           — current branch (symbolic ref) or detached SHA
.git/ORIG_HEAD      — saved by merge/rebase/reset for undo (git reset ORIG_HEAD)
.git/MERGE_HEAD     — the commit being merged (during active merge)
.git/FETCH_HEAD     — last fetched ref (git fetch sets this)
.git/CHERRY_PICK_HEAD — commit being cherry-picked (during conflict)
.git/REBASE_HEAD    — commit being replayed (during rebase conflict)
```

```bash
cat .git/HEAD          # shows: ref: refs/heads/main
cat .git/ORIG_HEAD     # SHA before last disruptive operation
git show ORIG_HEAD     # inspect what you had before the merge/rebase

# List all refs
git for-each-ref --format='%(refname) %(objectname:short)' refs/
```

### Loose Objects vs Packfiles

Objects start as loose files (one file per object). `git gc` runs `git pack-objects` to bundle thousands of objects into a single `.pack` file with a `.idx` index for O(log n) lookup. Packfiles use delta compression across similar objects.

```bash
# Manual GC
git gc --aggressive --prune=now

# Check object count
git count-objects -v

# Find packfiles
ls .git/objects/pack/

# Verify pack integrity
git verify-pack -v .git/objects/pack/pack-<sha>.idx | head -20
```

---

## 2. git log: Forensic History Reading

```bash
# Canonical decorated graph view
git log --oneline --graph --decorate --all

# Filter by author
git log --author="Jane Doe" --since="2024-01-01" --until="2024-06-01"

# Search commit messages
git log --grep="JIRA-1234" --regexp-ignore-case

# Pickaxe: find commits that added/removed a string
git log -S "secretKey" --source --all

# Regex diff: find commits where diff matches pattern
git log -G "password\s*=" --all -p

# Follow a file through renames
git log --follow --oneline -- src/utils/old-name.ts

# Show stat summary per commit
git log --stat --no-merges

# Show only merge commits
git log --merges --oneline

# Commits reachable from A but not B (B..A notation)
git log main..feature/my-branch

# Symmetric difference (commits in either, not in both)
git log main...feature/my-branch --left-right --oneline
```

---

## 3. Rebasing Deep Dive

### Interactive Rebase

```bash
git rebase -i HEAD~8       # interactive rebase last 8 commits
git rebase -i <base-sha>   # rebase everything after base-sha
```

Commands available in the editor:
```
pick   — keep commit as-is
reword — keep commit, edit message
edit   — pause to amend files/message (git commit --amend, then git rebase --continue)
squash — meld into previous commit, combine messages
fixup  — meld into previous commit, discard this message
drop   — remove commit entirely
exec   — run shell command between commits
break  — pause here (for manual inspection)
```

### Autosquash with fixup! Commits

Create fixup commits that autosquash into their target:

```bash
# Create a fixup for a specific commit
git commit --fixup=<sha-of-commit-to-fix>
# Creates commit message: "fixup! <original message>"

# Create a squash (preserves message)
git commit --squash=<sha>

# Autosquash: reorder and mark fixup!/squash! commits automatically
git rebase -i --autosquash main

# Set globally so you never forget
git config --global rebase.autoSquash true
```

### rebase --onto: Transplanting Branches

The most powerful rebase form: `git rebase --onto <newbase> <upstream> <branch>`

```bash
# Scenario: feature was branched off a topic branch, not main
# main → topic → feature
# Goal: move feature's commits directly onto main

git rebase --onto main topic feature
# Takes commits reachable from feature but NOT from topic
# Replays them onto main

# Move last 3 commits to a different branch
git rebase --onto main HEAD~3

# Remove commits from the middle of a branch
# (detach commits after the range from their parent)
git rebase --onto feature~5 feature~3 feature
# Drops the 2 commits between HEAD~5 and HEAD~3
```

### When NOT to Rebase

**Never rebase public/shared branches.** Rebase rewrites SHAs. If teammates have built on the old SHAs, they face nightmare divergence. The test: "Has anyone else fetched this branch?" If yes, merge instead.

Safe: rebasing a local feature branch before opening a PR (cleaning up WIP commits).
Unsafe: rebasing `develop`, `main`, or any branch others have checked out.

### Force-Push Safely

```bash
# WRONG — blindly overwrites remote
git push --force origin feature/my-branch

# RIGHT — fails if remote has commits you haven't seen
git push --force-with-lease origin feature/my-branch

# Even safer: explicit lease
git push --force-with-lease=feature/my-branch:<expected-sha> origin feature/my-branch

# Set as default alias
git config --global alias.fpush 'push --force-with-lease'
```

---

## 4. Cherry-Pick

```bash
# Single commit
git cherry-pick <sha>

# Range of commits (exclusive start, inclusive end)
git cherry-pick A..B     # commits after A up to and including B

# Include A itself
git cherry-pick A^..B

# Append original SHA in commit message body
git cherry-pick -x <sha>
# Adds: "(cherry picked from commit <original-sha>)"

# Cherry-pick without committing (stage only)
git cherry-pick --no-commit <sha>

# Multiple discrete commits
git cherry-pick sha1 sha3 sha7

# During conflict
git cherry-pick --continue    # after resolving
git cherry-pick --abort       # abandon entirely
git cherry-pick --skip        # skip this commit, continue series
```

---

## 5. git bisect: Binary Search for Regressions

```bash
# Start bisect session
git bisect start
git bisect bad                  # current commit is bad
git bisect good v2.3.0          # last known good tag/sha

# Git checks out midpoint. Test, then mark:
git bisect good                 # if test passes
git bisect bad                  # if test fails
# Repeat until Git identifies the first bad commit

# Automated bisect with a test script (exit 0 = good, exit 1 = bad)
git bisect run ./test.sh

# Real example: npm test returns 0/1
git bisect run npm test -- --testPathPattern="auth.test.ts"

# View bisect log
git bisect log

# Save log and replay on another machine
git bisect log > bisect.log
git bisect replay bisect.log

# End session (returns to original HEAD)
git bisect reset

# Bisect with skip (untestable commits, e.g. build broken)
git bisect skip <sha>
git bisect skip <sha1> <sha2>
```

---

## 6. Reflog Recovery: Nothing Is Ever Truly Lost

The reflog records every time HEAD or a branch ref moves. Entries expire after 90 days by default (`gc.reflogExpire`).

```bash
# Show reflog for HEAD
git reflog

# Show reflog for a specific branch
git reflog show feature/my-branch

# Recover a deleted branch
git reflog                          # find the SHA of the branch tip before deletion
git checkout -b feature/restored <sha>

# Recover after accidental hard reset
git reflog                          # find entry before: "reset: moving to..."
git reset --hard HEAD@{3}           # restore to that point

# Time-based reflog navigation
git checkout HEAD@{2.hours.ago}
git checkout HEAD@{yesterday}

# Dangling objects (unreachable but not yet GC'd)
git fsck --lost-found               # writes dangling blobs/commits to .git/lost-found/
git fsck --unreachable | grep commit

# Inspect dangling commit
git show <dangling-sha>

# Restore it to a branch
git checkout -b recovered-work <dangling-sha>
```

---

## 7. Branching Strategies

### GitFlow

Designed by Vincent Driessen. Five permanent/semi-permanent branch types:

```
main        — production-ready code only, tagged releases
develop     — integration branch, next release
feature/*   — branch from develop, merge back to develop
release/*   — branch from develop when code freeze, merge to main+develop
hotfix/*    — branch from main for critical production fixes, merge to main+develop
```

```bash
# Feature start
git checkout -b feature/JIRA-123-user-auth develop

# Feature complete
git checkout develop
git merge --no-ff feature/JIRA-123-user-auth  # --no-ff preserves branch history
git branch -d feature/JIRA-123-user-auth

# Release branch
git checkout -b release/1.4.0 develop
# bump version, changelog only
git checkout main && git merge --no-ff release/1.4.0
git tag -a v1.4.0 -m "Release 1.4.0"
git checkout develop && git merge --no-ff release/1.4.0
git branch -d release/1.4.0
```

GitFlow suits: teams with scheduled releases, strong release/QA gates, compliance environments.
GitFlow struggles with: continuous delivery, frequent deploys, small teams.

### GitHub Flow

Single `main` branch, always deployable:

```
1. Branch from main: feature/description or fix/description
2. Commit early and often
3. Open PR (can be draft)
4. CI runs, review happens
5. Merge to main (squash or merge commit)
6. Deploy immediately from main
7. Delete branch
```

Suits: continuous deployment, small-to-medium teams, SaaS products.

### Trunk-Based Development (TBD)

All developers commit to `trunk` (main) at least daily. Feature branches live <2 days.

```bash
# Short-lived branch pattern
git checkout -b feature/small-atomic-change
# Work, commit, push
git push origin feature/small-atomic-change
# Open PR → CI → merge → delete (all within 1-2 days)
```

Long-lived features use **feature flags** (LaunchDarkly, Flagsmith, OpenFeature) to hide incomplete work. This is what Google, Facebook, and Netflix actually use at scale.

### Release Trains

Large org pattern (Google, Microsoft):
- Fixed release cadence (e.g., every 2 weeks)
- All work that passes cut-off rides the train
- Work not ready waits for next train
- Release branch cut from trunk at freeze
- Only critical fixes cherry-picked onto release branch

---

## 8. Submodules vs Subtree

### Git Submodules

```bash
# Add submodule
git submodule add https://github.com/org/lib.git vendor/lib
# Creates .gitmodules and a special "gitlink" entry in the tree

# Clone repo with submodules
git clone --recurse-submodules https://github.com/org/main.git

# Initialize after a plain clone
git submodule update --init --recursive

# Update all submodules to latest on their tracked branch
git submodule update --remote --merge

# Pitfall: pushing main repo without pushing submodule changes first
git push --recurse-submodules=check    # fail if submodule not pushed
git push --recurse-submodules=on-demand # auto-push submodules

# Remove a submodule (all 4 steps required)
git submodule deinit vendor/lib
git rm vendor/lib
rm -rf .git/modules/vendor/lib
git commit -m "remove submodule lib"
```

Submodule pitfalls:
1. Forgetting `--recurse-submodules` on clone/pull leaves empty directories
2. Submodule pointer diverges if developer forgets to push submodule changes before pushing parent
3. Detached HEAD in submodule directory confuses many developers
4. CI must explicitly init/update submodules

### Git Subtree

No `.gitmodules`. The external code is copied into the repo as regular commits.

```bash
# Add subtree (merges external repo history)
git subtree add --prefix vendor/lib https://github.com/org/lib.git main --squash

# Update from upstream
git subtree pull --prefix vendor/lib https://github.com/org/lib.git main --squash

# Push changes back upstream (contribute back)
git subtree push --prefix vendor/lib https://github.com/org/lib.git feature/my-fix
```

Subtree advantages: simpler for contributors (no submodule knowledge needed), works with `git clone` without flags.
Subtree disadvantages: history pollution if not squashed, harder to contribute back, no version pinning record.

---

## 9. Monorepo Strategies

### Turborepo

```bash
# Install
npm install turbo -D

# turbo.json pipeline
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],  # ^ = depends on dependencies' build first
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": []
    },
    "lint": {
      "outputs": []
    }
  }
}

# Run affected tasks only (uses content hashing for cache)
turbo run build --filter=...affected-package
turbo run test --filter=./packages/auth...  # auth and everything that depends on it
turbo run build --dry=json  # preview what would run
```

### Nx

```bash
# Generate affected list (for CI)
npx nx affected:build --base=main --head=HEAD
npx nx affected:test --base=origin/main
npx nx affected:lint

# Dependency graph visualization
npx nx graph

# Run specific project
npx nx build my-app
npx nx test my-lib --watch
```

### Bazel

```python
# BUILD file example
cc_library(
    name = "auth_lib",
    srcs = ["auth.cc"],
    hdrs = ["auth.h"],
    deps = ["//crypto:hasher"],
    visibility = ["//visibility:public"],
)

cc_test(
    name = "auth_test",
    srcs = ["auth_test.cc"],
    deps = [":auth_lib", "@gtest//:gtest_main"],
)
```

```bash
# Build only what changed
bazel build //... --build_tag_filters=-expensive

# Test affected targets
bazel test //auth/... //api/...

# Remote cache for distributed builds
bazel build //... --remote_cache=grpc://cache.internal:9092
```

### CODEOWNERS in Monorepos

```
# .github/CODEOWNERS
# Root default owner
*                        @org/platform-team

# Package-level ownership
/packages/auth/          @org/identity-team
/packages/payments/      @org/payments-team
/services/api-gateway/   @org/gateway-team

# Infrastructure
/terraform/              @org/sre-team
/.github/workflows/      @org/devops-team

# Docs
*.md                     @org/docs-team
```

### Sparse Checkout for Large Monorepos

```bash
# Clone without checking out any files
git clone --filter=blob:none --sparse https://github.com/org/monorepo.git
cd monorepo

# Enable cone mode (fast, directory-based patterns)
git sparse-checkout init --cone

# Check out only what you need
git sparse-checkout set packages/auth packages/shared services/api

# Add more directories later
git sparse-checkout add packages/payments

# List what's currently checked out
git sparse-checkout list
```

Partial clone (`--filter=blob:none`) means blob contents are fetched on demand. Trees and commits are fetched upfront. Combined with sparse checkout, CI agents for the `auth` team never download the `payments` package's files.

---

## 10. Git Hooks

### Manual Hooks

Hooks live in `.git/hooks/`. Must be executable. Not committed by default.

```bash
# pre-commit: run linter
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
set -e
npx eslint --ext .ts,.tsx src/
EOF
chmod +x .git/hooks/pre-commit

# commit-msg: enforce conventional commits
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/sh
COMMIT_MSG=$(cat "$1")
PATTERN="^(feat|fix|docs|style|refactor|perf|test|ci|chore|revert)(\(.+\))?(!)?: .{1,72}"
if ! echo "$COMMIT_MSG" | grep -qE "$PATTERN"; then
  echo "ERROR: Commit message must follow Conventional Commits"
  echo "Example: feat(auth): add OAuth2 support"
  exit 1
fi
EOF
chmod +x .git/hooks/commit-msg
```

### Husky (Node.js Projects)

```bash
npm install --save-dev husky
npx husky init

# .husky/pre-commit
npm run lint-staged

# .husky/commit-msg
npx --no -- commitlint --edit $1

# package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.go": ["gofmt -w"]
  }
}
```

### Lefthook (Polyglot, Fast)

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    lint:
      glob: "*.{ts,tsx}"
      run: npx eslint {staged_files}
    format:
      glob: "*.go"
      run: gofmt -l {staged_files}
    security:
      run: git secrets --scan

pre-push:
  commands:
    tests:
      run: npm test -- --passWithNoTests

commit-msg:
  commands:
    conventional:
      run: npx commitlint --edit {1}
```

```bash
npm install --save-dev @evilmartians/lefthook
npx lefthook install
```

---

## 11. Git Worktrees

Multiple working trees from a single repository — no second clone needed:

```bash
# List current worktrees
git worktree list

# Add a new worktree for a branch
git worktree add ../project-hotfix hotfix/critical-bug

# Add and create a new branch
git worktree add -b feature/parallel-work ../project-feature main

# Remove a worktree
git worktree remove ../project-hotfix

# Prune stale worktree references
git worktree prune

# Use case: work on a hotfix while keeping feature work in progress
# Main working tree: /home/user/project (on feature/big-refactor)
# Hotfix worktree: /home/user/project-hotfix (on hotfix/sec-patch)
# Both share .git — no disk duplication of history
```

---

## 12. Git LFS

```bash
# Install Git LFS
git lfs install

# Track file patterns (writes to .gitattributes)
git lfs track "*.psd"
git lfs track "*.mp4"
git lfs track "assets/models/**"

# Verify .gitattributes
cat .gitattributes
# *.psd filter=lfs diff=lfs merge=lfs -text

# Check LFS status
git lfs status
git lfs ls-files

# Migrate existing large files to LFS (rewrites history)
git lfs migrate import --include="*.psd" --everything

# Prune old LFS objects from local cache
git lfs prune

# Clone with LFS (downloads LFS objects)
git clone --recurse-submodules https://github.com/org/project.git
# LFS objects downloaded automatically if git-lfs is installed

# Download without LFS objects (CI that doesn't need assets)
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/org/project.git
```

Storage backends: GitHub's default LFS storage, self-hosted (Gitea, GitLab), or S3-backed solutions (Minio).

---

## 13. Signing Commits

### GPG Signing

```bash
# Generate GPG key (use 4096-bit RSA or Ed25519)
gpg --full-generate-key

# List keys
gpg --list-secret-keys --keyid-format=long

# Configure Git to use a key
git config --global user.signingkey KEYID_HERE
git config --global commit.gpgsign true
git config --global tag.gpgSign true

# Sign a specific commit without global setting
git commit -S -m "signed commit"

# Verify signatures in log
git log --show-signature --oneline

# Export public key for GitHub/GitLab
gpg --armor --export KEYID_HERE
```

### SSH Signing (Git 2.34+)

```bash
# Configure SSH signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# Create allowed_signers file (for local verification)
echo "user@example.com namespaces=\"git\" $(cat ~/.ssh/id_ed25519.pub)" > ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers

# Verify
git log --show-signature
```

GitHub Vigilant Mode: when enabled, commits WITHOUT a verified signature are marked "Unverified" — high-assurance repositories should require this.

---

## 14. PR Workflow Best Practices

### Atomic Commits

Each commit = one logical change. Reviewers should be able to `git bisect` your PR. Bad: "WIP", "fix stuff", "more stuff". Good: `feat(auth): add JWT refresh token rotation`, `test(auth): add refresh token expiry edge case`.

### Branch Protection Rules (GitHub)

```yaml
# via GitHub API / Terraform (github_branch_protection resource)
Required status checks:
  - ci/build
  - ci/test
  - ci/lint
  - security/snyk

Required reviews: 2
Dismiss stale reviews on new push: true
Require review from CODEOWNERS: true
Require conversation resolution before merge: true
Restrict force pushes: true
Restrict deletions: true
Require linear history: false  # team preference
```

### PR Description Template (`.github/pull_request_template.md`)

```markdown
## Summary
<!-- What does this PR do? Link Jira/issue -->

## Changes
- 
- 

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing done (describe steps)

## Checklist
- [ ] No secrets committed
- [ ] Documentation updated
- [ ] Breaking change? (update CHANGELOG)
- [ ] Performance implications considered

## Screenshots (if UI change)
```

---

## 15. Conventional Commits and Semantic Versioning

### Conventional Commits Spec

Format: `<type>[optional scope][optional !]: <description>`

```
feat(api): add rate limiting middleware
fix(auth): resolve token refresh race condition
docs: update contributing guide
chore(deps): upgrade to React 18
refactor(db): extract connection pooling to separate module
perf(cache): use LRU eviction for session store
test(payments): add edge case for declined cards
ci: add parallel test sharding
revert: feat(api): add rate limiting middleware
```

Breaking changes:
```
feat(api)!: change authentication endpoint path
# OR
feat(api): change authentication endpoint

BREAKING CHANGE: /auth/login moved to /v2/auth/login
```

### Semantic Versioning from Commits

```
fix → PATCH (0.0.X)
feat → MINOR (0.X.0)
BREAKING CHANGE → MAJOR (X.0.0)
```

### Changesets (for libraries/monorepos)

```bash
npm install --save-dev @changesets/cli
npx changeset init

# Developer adds changeset with their PR
npx changeset
# Prompts: which packages changed, bump type, summary

# In CI: version all packages based on changesets
npx changeset version

# Publish
npx changeset publish
```

### semantic-release

```yaml
# .releaserc.json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    ["@semantic-release/npm", { "npmPublish": true }],
    "@semantic-release/github",
    ["@semantic-release/git", {
      "assets": ["CHANGELOG.md", "package.json"],
      "message": "chore(release): ${nextRelease.version} [skip ci]"
    }]
  ]
}
```

---

## 16. GitHub Actions CI Integration

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true   # cancel previous run when new push arrives

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [18, 20]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0       # full history (needed for semantic-release, git log)

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage

      - uses: actions/upload-artifact@v4
        with:
          name: coverage-${{ matrix.node }}
          path: coverage/

  # Separate job: semantic release only on main, only after all tests pass
  release:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
          fetch-depth: 0
      - run: npm ci
      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## 17. Anti-Hallucination Protocol

Before asserting anything about Git behavior, verify with actual commands:

1. **Object SHAs**: Always use `git cat-file -t <sha>` and `git cat-file -p <sha>` to confirm object type and contents — never invent SHAs or assume object structure.
2. **Command flags**: Test flags against the local Git version with `git <command> --help`. Flags vary between Git versions (e.g., `--filter` in clone requires Git 2.17+; SSH signing requires Git 2.34+).
3. **Reflog expiry**: The 90-day default (`gc.reflogExpire`) is correct but configurable. Confirm with `git config gc.reflogExpire`.
4. **Submodule behavior**: Always test submodule workflows in an isolated repo before documenting them — submodule edge cases (detached HEAD, recursive update) are frequently misunderstood.
5. **Hook availability**: Never claim a hook "runs automatically" without confirming it's executable and in `.git/hooks/` (or `core.hooksPath`). Hooks do NOT run in bare repos.
6. **Force-with-lease**: Understand that `--force-with-lease` without specifying the ref checks all remote-tracking refs in the refspec — it does NOT protect against races if `git fetch` was run just before the push.
7. **Rebase --onto syntax**: The three-argument form is `git rebase --onto <newbase> <upstream> [<branch>]`. Verify argument order before executing on production branches.
8. **Packfile delta compression**: Delta compression is between similar objects in a pack, not between revisions of the same file. Don't assert byte-level delta structure without `git verify-pack -v`.
9. **LFS migration**: `git lfs migrate import` rewrites history — always run on a backup/fork first and coordinate with all contributors.
10. **Signed commits**: GPG vs SSH signing produces different signature formats in the commit object. SSH signatures in `gpgsig` header require Git 2.34+ to verify correctly.
11. **Sparse checkout cone mode**: Cone mode only supports directory prefixes, not arbitrary glob patterns. Non-cone mode supports globs but is significantly slower for large repos.
12. **GitHub Actions path filters**: `paths:` in `on.push` or `on.pull_request` filters events. But if ALL changed files are excluded, the workflow is skipped entirely — which can mean required status checks never run and PRs become un-mergeable.

---

## 18. Self-Review Checklist

Before finalizing any Git advice or workflow design, verify:

- [ ] **Every command is syntactically correct** — run it or check `man git-<command>` for flag names.
- [ ] **SHA references use correct ancestor syntax** — `HEAD~3` (3 commits back) vs `HEAD^3` (third parent of a merge commit) are different.
- [ ] **Rebase destination is not a public/shared branch** — confirm before recommending `git rebase`.
- [ ] **`--force-with-lease` recommended everywhere `--force` appears** — flag every bare `--force` as a code smell.
- [ ] **Reflog commands include the reset path** — always tell users how to undo after reflog recovery.
- [ ] **Hook scripts include `set -e`** — hooks without `set -e` continue after errors silently.
- [ ] **GPG/SSH signing config specifies the correct key format** — `gpg.format ssh` vs default `openpgp` must match the key type.
- [ ] **Submodule instructions include all four removal steps** — missing any step leaves ghost state in `.git/modules/`.
- [ ] **Sparse checkout commands include `--cone` or explicit non-cone decision** — unspecified mode defaults to non-cone (slow).
- [ ] **LFS track patterns are committed to `.gitattributes`** — git lfs track writes to `.gitattributes` only; the file must be committed.
- [ ] **CI workflow concurrency groups use correct context variables** — `github.ref` vs `github.head_ref` for PR vs push events.
- [ ] **Conventional commit regex covers `!` for breaking changes** — many commit-lint configs miss the `!` shorthand.
- [ ] **Branch protection rule changes are coordinated** — enabling "require linear history" on a branch with existing merge commits breaks existing workflows.
- [ ] **git gc aggressive is not run on shared repositories during peak hours** — `--aggressive` is CPU/IO intensive and can spike latency.
- [ ] **All commands verified against documented Git version requirements** — state minimum Git version for any feature introduced after Git 2.20.
---
