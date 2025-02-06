import os
import git
import logging
import shutil
import stat
from typing import Optional
import time
import subprocess

class RepositoryHandler:
    def __init__(self, work_dir: str, logger: Optional[logging.Logger] = None):
        """Initialize repository handler with working directory"""
        self.work_dir = work_dir
        self.logger = logger or logging.getLogger('codeql_automation')
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

    def clone_repository(self, repo_url: str, branch: str) -> bool:
        """Clone a repository and checkout specified branch"""
        try:
            # Remove existing directory if it exists
            if os.path.exists(self.work_dir):
                self.logger.info(f"Removing existing directory: {self.work_dir}")
                self._safe_cleanup(self.work_dir)

            # Create parent directory if needed
            os.makedirs(os.path.dirname(self.work_dir), exist_ok=True)

            # Clone repository
            self.logger.info(f"Cloning {repo_url} branch {branch} to {self.work_dir}")
            cmd = [
                "git",
                "clone",
                "--branch",
                branch,
                "--single-branch",
                "--depth",
                "1",
                repo_url,
                self.work_dir
            ]

            process = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            self.logger.info("Repository cloned successfully")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {str(e)}")
            self.logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during cloning: {str(e)}")
            return False

    def cleanup(self) -> None:
        """Clean up the working directory"""
        # Commented out cleanup for now
        # try:
        #     if os.path.exists(self.work_dir):
        #         self.logger.info(f"Cleaning up directory: {self.work_dir}")
        #         self._safe_cleanup(self.work_dir)
        #         self.logger.info("Cleanup completed successfully")
        # except Exception as e:
        #     self.logger.error(f"Error during cleanup: {str(e)}")
        pass