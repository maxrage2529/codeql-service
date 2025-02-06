import os
import sys
import subprocess
import logging
from typing import Optional

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.repository_handler import RepositoryHandler
from src.utils import setup_logging, load_config

def clone_repo(
        repo_url: str,
        branch: str,
        work_dir: str,
        logger: logging.Logger = None
) -> Optional[str]:
    """
    Clone a repository and checkout specified branch

    Args:
        repo_url: URL of the repository to clone
        branch: Branch to checkout
        work_dir: Directory to clone the repository into
        logger: Logger instance

    Returns:
        Path to cloned repository
    """
    if logger is None:
        logger = logging.getLogger('codeql_automation')

    try:
        # Ensure work directory exists
        os.makedirs(work_dir, exist_ok=True)

        # Clone repository
        logger.info(f"Cloning repository: {repo_url}")
        clone_cmd = [
            "git",
            "clone",
            "--branch",
            branch,
            "--single-branch",
            "--depth",
            "1",
            repo_url,
            work_dir
        ]

        process = subprocess.run(
            clone_cmd,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Successfully cloned repository to: {work_dir}")
        return work_dir

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {str(e)}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during cloning: {str(e)}")
        return None

def main():
    try:
        # Configuration
        config_path = os.path.join(project_root, 'config', 'config.yaml')
        config = load_config(config_path)

        log_dir = config['output']['log_dir']
        work_dir = "./workspace"

        # Setup logging
        logger = setup_logging(log_dir)
        if not logger:
            raise RuntimeError("Failed to initialize logger")

        # Create workspace directory if it doesn't exist
        os.makedirs(work_dir, exist_ok=True)

        # Process each repository from config
        for repo_config in config['repositories']:
            repo_url = repo_config['url']
            branch = repo_config['branch']

            logger.info(f"Processing repository: {repo_url}, branch: {branch}")

            # Clone repository
            repo_path = clone_repo(
                repo_url=repo_url,
                branch=branch,
                work_dir=work_dir,
                logger=logger
            )

            if repo_path:
                logger.info(f"Successfully cloned {repo_url}")
            else:
                logger.error(f"Failed to clone {repo_url}")

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 