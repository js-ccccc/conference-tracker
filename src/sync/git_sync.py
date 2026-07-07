"""Git 自动提交与推送"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from git import Repo, InvalidGitRepositoryError

logger = logging.getLogger(__name__)


class GitSync:
    """使用 GitPython 自动 commit + push"""

    def __init__(self, repo_path: str | Path | None = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.repo: Repo | None = None
        try:
            self.repo = Repo(self.repo_path)
        except InvalidGitRepositoryError:
            logger.warning("Not a git repository: %s", self.repo_path)

    def commit_and_push(
        self,
        paths: list[str],
        message: str | None = None,
        push: bool = True,
    ) -> bool:
        if not self.repo:
            logger.error("Git repository not available")
            return False

        if self.repo.bare:
            logger.error("Bare repository, cannot commit")
            return False

        for path in paths:
            rel_path = str(Path(path).relative_to(self.repo_path))
            if Path(self.repo_path / rel_path).exists():
                self.repo.index.add([rel_path])

        if not self.repo.is_dirty() and not self.repo.index.diff("HEAD"):
            logger.info("No changes to commit")
            return False

        commit_msg = message or f"Auto update: {datetime.now().strftime('%Y-%m-%d')}"
        author = self._get_git_actor()
        self.repo.index.commit(commit_msg, author=author, committer=author)
        logger.info("Committed: %s", commit_msg)

        if push:
            self._push()

        return True

    def _get_git_actor(self):
        from git import Actor

        return Actor(
            os.getenv("GIT_USER_NAME", "github-actions[bot]"),
            os.getenv(
                "GIT_USER_EMAIL",
                "github-actions[bot]@users.noreply.github.com",
            ),
        )

    def _push(self) -> None:
        assert self.repo is not None
        try:
            origin = self.repo.remote("origin")
            token = os.getenv("GITHUB_TOKEN")
            if token:
                url = origin.url
                if url.startswith("https://") and "@" not in url:
                    push_url = url.replace(
                        "https://", f"https://x-access-token:{token}@"
                    )
                    with origin.url.set_url(push_url):
                        origin.push()
                else:
                    origin.push()
            else:
                origin.push()
            logger.info("Pushed to remote")
        except Exception as exc:
            logger.error("Push failed: %s", exc)
