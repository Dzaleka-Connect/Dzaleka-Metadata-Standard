"""
DMS Git Synchronization

Handles automated git backups of the records directory to a central remote,
designed gracefully for offline-first environments.
"""

import subprocess
import shutil
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()


def _run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the specified directory."""
    if not shutil.which("git"):
        raise RuntimeError("Git is not installed or not in PATH.")
    
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check
    )


def ensure_git_repo(directory: Path):
    """Ensure the directory is a git repository, initializing if necessary."""
    res = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=directory, check=False)
    if res.returncode != 0:
        console.print("  [dim]Initializing new git repository...[/dim]")
        _run_git(["init"], cwd=directory)
        _run_git(["branch", "-M", "main"], cwd=directory)


def set_remote(directory: Path, remote_url: str):
    """Set or update the origin remote URL."""
    res = _run_git(["remote", "-v"], cwd=directory, check=False)
    
    if "origin" in res.stdout:
        _run_git(["remote", "set-url", "origin", remote_url], cwd=directory)
    else:
        _run_git(["remote", "add", "origin", remote_url], cwd=directory)
    console.print(f"  [dim]Remote 'origin' set to {remote_url}[/dim]")


def sync_records(directory: str | Path, remote: str | None = None, message: str | None = None):
    """Synchronize records using Git (add, commit, push)."""
    dir_path = Path(directory).resolve()
    
    if not dir_path.exists():
        console.print(f"[red]Error: Directory {dir_path} does not exist.[/red]")
        raise SystemExit(1)
        
    try:
        ensure_git_repo(dir_path)
        
        if remote:
            set_remote(dir_path, remote)
            
        # Stage all JSON files
        _run_git(["add", "*.json"], cwd=dir_path, check=False)
        
        # Check if there's anything to commit
        status = _run_git(["status", "--porcelain"], cwd=dir_path)
        if not status.stdout.strip():
            console.print("  [green]✓ All records are already saved in the local archive history.[/green]")
        else:
            # Commit changes
            msg = message or f"DMS automated sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            _run_git(["commit", "-m", msg], cwd=dir_path)
            console.print("  [green]✓ Records successfully committed to local authentic archive.[/green]")
            
        # Push to remote if origin exists
        remotes = _run_git(["remote"], cwd=dir_path)
        if "origin" in remotes.stdout:
            console.print("  [dim]Pushing to central repository...[/dim]")
            push_res = _run_git(["push", "-u", "origin", "main"], cwd=dir_path, check=False)
            
            if push_res.returncode == 0:
                console.print("  [bold green]✓ Successfully synced with central Dzaleka Connect archive![/bold green]")
            else:
                console.print("  [yellow]⚠ Local backup successful, but could not push to remote. Are you offline?[/yellow]")
                console.print("    [dim]Your work is perfectly safe locally. Try syncing again when connected to the internet.[/dim]")
        else:
            console.print("  [dim]No remote configured. Skipping push. Use --remote to set one up.[/dim]")

    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Please install Git to use the sync feature: https://git-scm.com/downloads[/yellow]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise SystemExit(1)
