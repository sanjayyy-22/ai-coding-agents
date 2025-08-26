"""Git operations tool."""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from git import Repo, InvalidGitRepositoryError
from .base import BaseTool, ToolResult, ToolResultStatus


class GitTool(BaseTool):
    """Tool for Git operations."""
    
    def __init__(self):
        super().__init__()
        self.name = "git"
    
    @property
    def description(self) -> str:
        return "Perform Git version control operations like status, diff, commit, branch management"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["status", "diff", "add", "commit", "push", "pull", "branch", "checkout", "log", "stash", "reset"],
                    "description": "The Git operation to perform"
                },
                "path": {
                    "type": "string",
                    "description": "Repository path (optional, defaults to current directory)"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files to operate on (for add, commit operations)"
                },
                "message": {
                    "type": "string",
                    "description": "Commit message"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name for branch operations"
                },
                "remote": {
                    "type": "string",
                    "default": "origin",
                    "description": "Remote name for push/pull operations"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of entries for log operations"
                }
            },
            "required": ["operation"]
        }
    
    def is_safe_operation(self, **kwargs) -> bool:
        """Check if operation is safe."""
        operation = kwargs.get("operation", "")
        
        # Operations that modify the repository require approval
        destructive_ops = ["commit", "push", "reset", "checkout"]
        if operation in destructive_ops:
            return False
        
        return True
    
    def get_preview(self, **kwargs) -> str:
        """Get operation preview."""
        operation = kwargs.get("operation", "")
        
        if operation == "commit":
            message = kwargs.get("message", "")
            files = kwargs.get("files", [])
            return f"Commit changes with message: '{message}'" + (f" (files: {files})" if files else "")
        elif operation == "push":
            remote = kwargs.get("remote", "origin")
            branch = kwargs.get("branch", "current")
            return f"Push to {remote}/{branch}"
        elif operation == "reset":
            return "Reset repository state"
        elif operation == "checkout":
            branch = kwargs.get("branch", "")
            return f"Checkout branch: {branch}"
        else:
            return f"Execute git {operation}"
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute Git operation."""
        operation = kwargs.get("operation")
        repo_path = kwargs.get("path", ".")
        
        try:
            # Initialize repository
            try:
                repo = Repo(repo_path)
            except InvalidGitRepositoryError:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Not a Git repository: {repo_path}",
                    suggested_actions=["Initialize with 'git init'", "Check if you're in the right directory"]
                )
            
            if operation == "status":
                return await self._git_status(repo)
            elif operation == "diff":
                return await self._git_diff(repo, kwargs.get("files"))
            elif operation == "add":
                files = kwargs.get("files", [])
                return await self._git_add(repo, files)
            elif operation == "commit":
                message = kwargs.get("message", "")
                files = kwargs.get("files", [])
                return await self._git_commit(repo, message, files)
            elif operation == "push":
                remote = kwargs.get("remote", "origin")
                branch = kwargs.get("branch")
                return await self._git_push(repo, remote, branch)
            elif operation == "pull":
                remote = kwargs.get("remote", "origin")
                branch = kwargs.get("branch")
                return await self._git_pull(repo, remote, branch)
            elif operation == "branch":
                return await self._git_branch(repo, kwargs.get("branch"))
            elif operation == "checkout":
                branch = kwargs.get("branch", "")
                return await self._git_checkout(repo, branch)
            elif operation == "log":
                limit = kwargs.get("limit", 10)
                return await self._git_log(repo, limit)
            elif operation == "stash":
                return await self._git_stash(repo)
            elif operation == "reset":
                return await self._git_reset(repo, kwargs.get("files"))
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Unknown Git operation: {operation}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
                suggested_actions=[
                    "Check Git repository status",
                    "Verify Git is installed",
                    "Check network connection for remote operations"
                ]
            )
    
    async def _git_status(self, repo: Repo) -> ToolResult:
        """Get repository status."""
        try:
            # Get current branch
            current_branch = repo.active_branch.name if repo.active_branch else "HEAD"
            
            # Get modified files
            modified_files = [item.a_path for item in repo.index.diff(None)]
            
            # Get staged files
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            
            # Get untracked files
            untracked_files = repo.untracked_files
            
            # Check if repository is dirty
            is_dirty = repo.is_dirty()
            
            status_info = {
                "branch": current_branch,
                "is_dirty": is_dirty,
                "modified_files": modified_files,
                "staged_files": staged_files,
                "untracked_files": untracked_files,
                "ahead": 0,  # Would need remote tracking to calculate
                "behind": 0
            }
            
            status_summary = []
            if staged_files:
                status_summary.append(f"{len(staged_files)} staged files")
            if modified_files:
                status_summary.append(f"{len(modified_files)} modified files")
            if untracked_files:
                status_summary.append(f"{len(untracked_files)} untracked files")
            
            if not status_summary:
                content = f"On branch {current_branch}. Working tree clean."
            else:
                content = f"On branch {current_branch}. {', '.join(status_summary)}."
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data=status_info
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to get status: {str(e)}"
            )
    
    async def _git_diff(self, repo: Repo, files: Optional[List[str]] = None) -> ToolResult:
        """Get repository diff."""
        try:
            if files:
                # Diff specific files
                diffs = []
                for file_path in files:
                    diff = repo.git.diff(file_path)
                    if diff:
                        diffs.append(f"--- {file_path} ---\n{diff}")
                diff_content = "\n\n".join(diffs)
            else:
                # Diff all changes
                diff_content = repo.git.diff()
            
            if not diff_content:
                content = "No changes to show"
            else:
                content = f"Diff output:\n{diff_content[:2000]}..."  # Truncate for display
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={
                    "diff": diff_content,
                    "files": files or "all",
                    "has_changes": bool(diff_content)
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to get diff: {str(e)}"
            )
    
    async def _git_add(self, repo: Repo, files: List[str]) -> ToolResult:
        """Add files to staging area."""
        try:
            if not files:
                # Add all files
                repo.git.add(".")
                added_files = "all files"
            else:
                # Add specific files
                for file_path in files:
                    repo.index.add([file_path])
                added_files = ", ".join(files)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Added {added_files} to staging area",
                data={"files": files or ["all"]}
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to add files: {str(e)}"
            )
    
    async def _git_commit(self, repo: Repo, message: str, files: Optional[List[str]] = None) -> ToolResult:
        """Commit changes."""
        try:
            if not message:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="Commit message is required"
                )
            
            # Add files if specified
            if files:
                for file_path in files:
                    repo.index.add([file_path])
            
            # Check if there are changes to commit
            if not repo.index.diff("HEAD"):
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="No changes to commit"
                )
            
            # Create commit
            commit = repo.index.commit(message)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Created commit {commit.hexsha[:8]}: {message}",
                data={
                    "commit_hash": commit.hexsha,
                    "message": message,
                    "files": files or "staged files"
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to commit: {str(e)}"
            )
    
    async def _git_push(self, repo: Repo, remote: str = "origin", branch: Optional[str] = None) -> ToolResult:
        """Push changes to remote."""
        try:
            if not branch:
                branch = repo.active_branch.name
            
            # Push to remote
            origin = repo.remote(remote)
            push_info = origin.push(branch)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Pushed {branch} to {remote}",
                data={
                    "remote": remote,
                    "branch": branch,
                    "push_info": str(push_info)
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to push: {str(e)}",
                suggested_actions=[
                    "Check network connection",
                    "Verify remote repository exists",
                    "Check authentication credentials"
                ]
            )
    
    async def _git_pull(self, repo: Repo, remote: str = "origin", branch: Optional[str] = None) -> ToolResult:
        """Pull changes from remote."""
        try:
            if not branch:
                branch = repo.active_branch.name
            
            # Pull from remote
            origin = repo.remote(remote)
            pull_info = origin.pull(branch)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Pulled {branch} from {remote}",
                data={
                    "remote": remote,
                    "branch": branch,
                    "pull_info": str(pull_info)
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to pull: {str(e)}",
                suggested_actions=[
                    "Check network connection",
                    "Resolve any merge conflicts",
                    "Check authentication credentials"
                ]
            )
    
    async def _git_branch(self, repo: Repo, branch_name: Optional[str] = None) -> ToolResult:
        """List or create branches."""
        try:
            if branch_name:
                # Create new branch
                new_branch = repo.create_head(branch_name)
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content=f"Created branch: {branch_name}",
                    data={"branch": branch_name, "created": True}
                )
            else:
                # List branches
                branches = []
                current_branch = repo.active_branch.name if repo.active_branch else None
                
                for branch in repo.branches:
                    branches.append({
                        "name": branch.name,
                        "is_current": branch.name == current_branch
                    })
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content=f"Found {len(branches)} branches",
                    data={
                        "branches": branches,
                        "current_branch": current_branch
                    }
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to handle branches: {str(e)}"
            )
    
    async def _git_checkout(self, repo: Repo, branch: str) -> ToolResult:
        """Checkout a branch."""
        try:
            if not branch:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="Branch name is required"
                )
            
            # Check if branch exists
            if branch in [b.name for b in repo.branches]:
                repo.git.checkout(branch)
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content=f"Switched to branch: {branch}",
                    data={"branch": branch}
                )
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Branch '{branch}' does not exist",
                    suggested_actions=[f"Create branch with: git branch {branch}"]
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to checkout: {str(e)}"
            )
    
    async def _git_log(self, repo: Repo, limit: int = 10) -> ToolResult:
        """Get commit log."""
        try:
            commits = []
            for commit in repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat()
                })
            
            content = f"Recent {len(commits)} commits:\n"
            for commit in commits:
                content += f"  {commit['short_hash']} - {commit['message'][:50]}...\n"
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={"commits": commits, "limit": limit}
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to get log: {str(e)}"
            )
    
    async def _git_stash(self, repo: Repo) -> ToolResult:
        """Stash current changes."""
        try:
            # Check if there are changes to stash
            if not repo.is_dirty():
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content="No changes to stash"
                )
            
            repo.git.stash()
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content="Stashed current changes",
                data={"stashed": True}
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to stash: {str(e)}"
            )
    
    async def _git_reset(self, repo: Repo, files: Optional[List[str]] = None) -> ToolResult:
        """Reset changes."""
        try:
            if files:
                # Reset specific files
                for file_path in files:
                    repo.git.checkout("HEAD", file_path)
                content = f"Reset {len(files)} files"
            else:
                # Reset all changes
                repo.git.reset("--hard", "HEAD")
                content = "Reset all changes to HEAD"
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={"files": files or "all"}
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to reset: {str(e)}"
            )