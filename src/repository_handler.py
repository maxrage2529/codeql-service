import os
import git
import logging
import shutil
import stat
from typing import Optional
import time

class RepositoryHandler:
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.logger = logging.getLogger(__name__)
        self._ensure_directory(work_dir)

    def _ensure_directory(self, directory: str) -> None:
        """Create directory if it doesn't exist and ensure it's writable"""
        try:
            os.makedirs(directory, exist_ok=True)
            # Ensure directory has write permissions
            os.chmod(directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except Exception as e:
            self.logger.error(f"Failed to create/modify directory {directory}: {str(e)}")
            raise

    def _remove_readonly(self, func, path, excinfo):
        """Error handler for shutil.rmtree to handle readonly files"""
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        func(path)

    def _safe_cleanup(self, path: str) -> None:
        """Safely remove a directory and its contents"""
        if not os.path.exists(path):
            return

        # Make all files writable
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files + dirs:
                try:
                    full_path = os.path.join(root, name)
                    os.chmod(full_path, stat.S_IRWXU)
                except Exception as e:
                    self.logger.warning(f"Failed to change permissions for {full_path}: {str(e)}")

        # Try multiple times to remove the directory
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                shutil.rmtree(path, onerror=self._remove_readonly)
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    self.logger.error(f"Failed to remove directory {path} after {max_attempts} attempts: {str(e)}")
                else:
                    time.sleep(1)  # Wait before retry

    def clone_and_checkout(self, repo_url: str, branch: str) -> Optional[str]:
        """Clone a repository and checkout specified branch"""
        try:
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(self.work_dir, repo_name)

            self.logger.info(f"Starting repository processing for {repo_name}")
            
            # Clean up existing repository if it exists
            if os.path.exists(repo_path):
                self.logger.info(f"Removing existing repository at {repo_path}")
                self._safe_cleanup(repo_path)

            self.logger.info(f"Cloning repository {repo_name} from {repo_url}")
            repo = git.Repo.clone_from(repo_url, repo_path)
            
            self.logger.info(f"Checking out branch {branch}")
            repo.git.checkout(branch)
            
            self.logger.info(f"Successfully cloned and checked out {repo_name} at {repo_path}")
            return repo_path

        except git.GitCommandError as e:
            self.logger.error(f"Git operation failed for {repo_url}: {str(e)}")
            if "Remote branch {branch} not found" in str(e):
                self.logger.error(f"Branch {branch} does not exist in repository")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during repository handling: {str(e)}")
            self.logger.exception("Full traceback:")
            return None

    def cleanup(self, repo_path: str) -> None:
        """Clean up repository directory"""
        try:
            self._safe_cleanup(repo_path)
        except Exception as e:
            self.logger.error(f"Failed to cleanup repository at {repo_path}: {str(e)}") 