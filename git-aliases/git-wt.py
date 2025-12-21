#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

# -----------------------------------------------------------------------------
# ANSI colors
# -----------------------------------------------------------------------------

class C:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    DIM = "\033[2m"
    RESET = "\033[0m"

BRAILE_SPACE="⠀"

# -----------------------------------------------------------------------------
# subprocess helpers
# -----------------------------------------------------------------------------

def sh(cmd: List[str], *, cwd: Path | None = None, check: bool = True) -> str:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and p.returncode != 0:
        sys.stderr.write(p.stderr)
        sys.exit(p.returncode)
    return p.stdout.rstrip("\n")


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    return sh(["git", *args], cwd=cwd, check=check)


def require(cmd: str) -> None:
    if shutil.which(cmd) is None:
        sys.exit(f"{cmd} not found")


# -----------------------------------------------------------------------------
# repo / path helpers
# -----------------------------------------------------------------------------

def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel")).resolve()


def main_worktree() -> Path:
    """Get the main worktree (where .git is a directory, not a file)."""
    out = git("worktree", "list", "--porcelain")
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = Path(line.split(maxsplit=1)[1])
            if (path / ".git").is_dir():
                return path
    return repo_root()  # fallback


def repo_name() -> str:
    return repo_root().name


def worktree_base() -> Path:
    root = git("config", "--get", "wt.root", check=False)
    base = Path(root).expanduser().resolve() if root else repo_root().parent
    return base / repo_name()


# -----------------------------------------------------------------------------
# formatting helpers
# -----------------------------------------------------------------------------

def short_time(s: str) -> str:
    repl = {
        " seconds ago": "s",
        " minutes ago": "m",
        " hours ago": "h",
        " days ago": "d",
        " weeks ago": "w",
        " months ago": "mo",
        " years ago": "y",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def truncate_right(s: str, w: int) -> str:
    return s[: w - 1] + "…" if len(s) > w else s.ljust(w)


def truncate_left(s: str, w: int) -> str:
    return "…" + s[-(w - 1) :] if len(s) > w else s.ljust(w)


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_len(s: str) -> int:
    """Return the visible length of a string, ignoring ANSI codes."""
    return len(_ANSI_RE.sub("", s))


def pad_ansi(s: str, w: int) -> str:
    """Left-align string to width w, accounting for ANSI codes."""
    vis = visible_len(s)
    return s + " " * max(0, w - vis)


def relpath(p: Path) -> str:
    return str(p.resolve()).replace(str(Path.home()), "~")


# -----------------------------------------------------------------------------
# git worktree model
# -----------------------------------------------------------------------------

def worktrees() -> Iterable[Tuple[Path, str]]:
    out = git("worktree", "list", "--porcelain")
    wt: Path | None = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            wt = Path(line.split()[1])
        elif line.startswith("branch ") and wt:
            yield wt, line.split()[1].removeprefix("refs/heads/")


# -----------------------------------------------------------------------------
# subcommands
# -----------------------------------------------------------------------------

def cmd_new(branch: str) -> None:
    base = worktree_base()
    path = base / branch
    if path.exists():
        sys.exit(f"path already exists: {path}")
    base.mkdir(parents=True, exist_ok=True)

    if subprocess.call(
        ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) == 0:
        git("worktree", "add", str(path), branch)
    else:
        git("worktree", "add", "-b", branch, str(path))

    print(path)


def cmd_checkout(ref: str) -> None:
    base = worktree_base()
    base.mkdir(parents=True, exist_ok=True)

    # Check if it's a local branch
    if subprocess.call(
        ["git", "show-ref", "--verify", f"refs/heads/{ref}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) == 0:
        path = base / ref
        git("worktree", "add", str(path), ref)
        print(path)
        return

    # Check if it's a remote branch
    if subprocess.call(
        ["git", "show-ref", "--verify", f"refs/remotes/{ref}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) == 0:
        local = ref.split("/")[-1]
        path = base / local  # Use local branch name for path, not full remote ref
        git("worktree", "add", "-b", local, str(path), ref)
        print(path)
        return

    # Detached HEAD (commit hash, tag, etc.) - use short hash for path if it's a full hash
    path_name = ref[:12] if len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()) else ref
    path = base / path_name
    git("worktree", "add", "--detach", str(path), ref)
    print(path)


def cmd_prune(force: bool) -> None:
    prunable: List[Path] = []

    for path, _ in worktrees():
        # Skip stale worktrees (path no longer exists on disk)
        if not path.exists():
            continue

        # Skip main worktree (has .git directory, not file)
        git_path = path / ".git"
        if git_path.is_dir():
            continue

        if git("status", "--porcelain", cwd=path):
            continue

        if subprocess.call(
            ["git", "rev-parse", "@{u}"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) != 0:
            continue

        counts = git("rev-list", "--left-right", "--count", "HEAD...@{u}", cwd=path)
        if counts not in ("0\t0", "0 0"):
            continue

        prunable.append(path)

    if not prunable:
        print("No prunable worktrees found.")
        return

    print("The following worktrees are fully synced and will be removed:", file=sys.stderr)
    for p in prunable:
        print(f"  {p}", file=sys.stderr)

    if not force:
        try:
            sys.stderr.write("\nProceed? [y/N] ")
            sys.stderr.flush()
            confirm = input()
            if confirm.lower() != "y":
                return
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return

    for p in prunable:
        git("worktree", "remove", str(p))


# -----------------------------------------------------------------------------
# interactive selector
# -----------------------------------------------------------------------------

def interactive(remove: bool, print_path: bool, force: bool = False) -> None:
    # Use minimum 160 width so paths aren't over-truncated; fzf handles scrolling
    term_width = max(160, shutil.get_terminal_size(fallback=(160, 0)).columns)
    w_branch = 35  # Fixed width for branch name
    w_state, w_time, w_up = 6, 6, 7

    rows: List[str] = []

    for path, branch in worktrees():
        # Skip stale worktrees (path no longer exists on disk)
        if not path.exists():
            continue

        dirty = bool(git("status", "--porcelain", cwd=path))
        state = f"{C.RED}dirty{C.RESET}" if dirty else f"{C.GREEN}clean{C.RESET}"

        raw_time = git("log", "-1", "--pretty=%cr", cwd=path, check=False)
        time = f"{C.YELLOW}{short_time(raw_time)}{C.RESET}" if raw_time else ""

        has_up = subprocess.call(
            ["git", "rev-parse", "@{u}"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) == 0
        upstream = f"{C.BLUE}up{C.RESET}" if has_up else f"{C.MAGENTA}local{C.RESET}"

        # Two-line format: branch + metadata on line 1, path on line 2, separator line
        line1 = (
            f"{truncate_right(branch, w_branch)}"
            f"{pad_ansi(state, w_state)} "
            f"{pad_ansi(time, w_time)} "
            f"{pad_ansi(upstream, w_up)}"
        )
        line2 = f"{C.DIM}{relpath(path)}{C.RESET}"
        row = f"{line1}\n{line2}\t{path}\t{branch}"
        rows.append(row)

    if not rows:
        return

    p = subprocess.run(
        ["fzf", "--ansi", "--read0", "--multi-line", "--delimiter=\t", "--with-nth=1", "--gap", "--highlight-line"],
        input="\0".join(rows),
        text=True,
        stdout=subprocess.PIPE,
    )
    if not p.stdout:
        return

    parts = p.stdout.rstrip("\n").split("\t")
    selected = Path(parts[-2])
    branch = parts[-1]
    if remove:
        # Check if branch is fully merged before removing anything
        if not force:
            check = subprocess.run(
                ["git", "merge-base", "--is-ancestor", branch, "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if check.returncode != 0:
                sys.exit(f"{C.RED}Branch '{branch}' is not fully merged. Use -rf to force delete.{C.RESET}")

        # Get main repo path before removing worktree (in case we're inside it)
        main_repo = main_worktree()
        git("worktree", "remove", str(selected), cwd=main_repo)
        delete_flag = "-D" if force else "-d"
        del_result = subprocess.run(
            ["git", "branch", delete_flag, branch],
            cwd=main_repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if del_result.returncode == 0:
            print(del_result.stdout.rstrip())
        else:
            print(f"{C.YELLOW}Branch '{branch}' not deleted: {del_result.stderr.strip()}{C.RESET}")
    elif print_path:
        print(selected)


# -----------------------------------------------------------------------------
# entry point
# -----------------------------------------------------------------------------

def main() -> None:
    require("git")
    require("fzf")

    ap = argparse.ArgumentParser(
        description="Git worktree manager with fzf integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  new <branch>      Create worktree for new or existing branch
  checkout <ref>    Checkout branch/commit into worktree (alias: co)
  prune             Remove worktrees fully synced with upstream

examples:
  gwt                    Interactive worktree selector (cd into selection)
  gwt new feature-x      Create worktree for 'feature-x' branch
  gwt co origin/main     Checkout remote branch into worktree
  gwt -r                 Interactive remove worktree
  gwt -r -f              Remove worktree and force delete branch
  gwt prune              Remove fully-synced worktrees

shell setup:
  To enable cd functionality, source the companion 'gwt' shell script:
    echo "source $(pwd)/gwt" >> ~/.zshrc

config:
  Set a custom root directory for worktrees (default: parent of repo):
    git config --global wt.root ~/worktrees
""",
    )
    ap.add_argument("-r", "--remove", action="store_true", help="remove selected worktree")
    ap.add_argument("-f", "--force", action="store_true", help="force (prune: skip confirm, -r: delete unmerged branch)")
    ap.add_argument("-n", "--no-interactive", action="store_true", help="non-interactive mode")
    ap.add_argument("--print-path", action="store_true", help="print path instead of cd")
    ap.add_argument("cmd", nargs="?", metavar="CMD", help="new|checkout|co|prune")
    ap.add_argument("arg", nargs="?", metavar="ARG", help="branch name or ref")

    args = ap.parse_args()

    if args.cmd == "new":
        if not args.arg:
            sys.exit("branch name required")
        cmd_new(args.arg)

    elif args.cmd in ("checkout", "co"):
        if not args.arg:
            sys.exit("ref required")
        cmd_checkout(args.arg)

    elif args.cmd == "prune":
        cmd_prune(force=args.force or args.no_interactive)

    else:
        if args.no_interactive:
            if args.print_path:
                print(Path.cwd())
                return
            sys.exit("non-interactive mode requires explicit command")
        interactive(args.remove, args.print_path, args.force)


if __name__ == "__main__":
    main()
