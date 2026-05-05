
# Development Flow

## Branch Strategy

As shown in the diagram below, the feature branches (`feature/xxx`) are created from the `main` branch for development. The `main` branch is the release branch.

```mermaid
gitGraph LR:
  commit tag:"release-v1.0.0"
  branch feature/xxx
  commit
  commit
  checkout main
  branch feature/yyy
  commit
  checkout main
  merge feature/yyy
  checkout feature/xxx
  commit
  checkout main
  merge feature/xxx
  commit tag:"release-v1.1.0"
  checkout main
  branch hotfix/zzz
  commit
  commit
  checkout main
  merge hotfix/zzz
  commit tag:"release-v1.2.0"
```

### Branch Naming

While there are no strict rules, the following naming conventions are recommended:

- `feature/xxx`: (xxx represents the feature being added)
- `bugfix/xxx`: (xxx represents the bug being fixed)
- `hotfix/xxx`: (xxx represents the urgent fix)

## Automated Checks (pre-commit)

This project uses [`uv-pre-commit`](https://docs.astral.sh/uv/guides/integration/pre-commit/) to ensure code quality and consistency.
When you run `git commit`, the following checks are automatically executed:

- uv-lock: Ensures `pyproject.toml` and `uv.lock` are in sync (prevents version mismatch).
- Ruff: Automatically lints and formats your code.
- Mypy: Performs static type checking.

If any check fails, the commit will be aborted. You must fix the issues (e.g., run `uv lock` to sync the lockfile or fix linting errors) and run `git commit` again.

## Conventional Commits

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

### Commit Message Format

This repository provides a `.gitmessage` template for commit messages.
When you run `make install`, Git is automatically configured to use this template.
After that, running `git commit` will display the template in your configured editor.

```bash
git commit
# Overview (Uncomment one of the following templates)
#feat:
# └  A new feature
#fix:
# └  A bug fix
#docs:
# └  Documentation only changes
#style:
# └  Changes that do not affect the meaning of the code
#    (white-space, formatting, missing semi-colons, etc)
#refactor:
# └  A code change that neither fixes a bug nor adds a feature
#test:
# └  Adding missing or correcting existing tests
#ci:
# └  Changes to our CI configuration files and scripts
#chore:
# └  Updating grunt tasks etc; no production code change
```

Select the appropriate template and uncomment it, then write your commit message.

```bash
docs: Update README.md
# └  Documentation only changes
```

## Correspondence between Commit Messages and Labels

When a pull request is opened, labels are automatically assigned based on the commit message prefix.
Below is the correspondence between prefixes and labels:

| Prefix | Label | Description |
|---|---|---|
|feat: | `feature` | Adding a new feature |
|fix: | `bugfix` | Bug fixes |
|docs: | `documentation` | Documentation only changes |
|style: | `style` | Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc) |
|refactor: | `refactor` | Code changes that neither fix a bug nor add a feature |
|test: | `test` | Adding or correcting existing tests |
|ci: | `ci` | Adding or updating CI configuration and scripts |
|chore: | `chore` | Minor changes or maintenance tasks |

## CI

This project uses GitHub Actions to automate checks and repository management.

### Automated Checks

On pull requests, the following checks are automatically executed:

- linting and formatting (ruff)
- static type checking (mypy)
- tests (pytest)

Ensure that all checks pass before merging.

### Labeling

Labels are automatically assigned to pull requests targeting the default
branch based on the commit message prefix (see [Conventional Commits](#conventional-commits)).
