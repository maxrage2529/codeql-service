import os
import sys
import subprocess
import glob
import logging
from typing import List, Dict

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils import setup_logging, load_config

def get_language_build_config(language: str, repo_path: str) -> Dict[str, str]:
    """
    Get build configuration for specific language with proper compile command
    """
    if language == "java":
        # Find all Java files in the repository
        java_files = glob.glob(os.path.join(repo_path, "*.java"))
        if java_files:
            # Get just the file names without path for Java compilation
            java_file_names = " ".join(os.path.basename(f) for f in java_files)
            return {
                "command": f"javac {java_file_names}",
                "needs_build": True
            }

    return {
        "needs_build": False
    }

def create_codeql_database(
        repo_path: str,
        database_name: str,
        output_dir: str,
        languages: List[str],
        logger: logging.Logger = None
) -> str:
    """
    Create a CodeQL database for a repository with multiple language support
    """
    if logger is None:
        logger = logging.getLogger('codeql_automation')

    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Base command for all languages
        base_cmd = [
            "codeql",
            "database",
            "create",
            "--overwrite",
            "--source-root",
            repo_path
        ]

        database_path = os.path.join(output_dir, f"{database_name}_db")

        # If multiple languages, use db-cluster
        if len(languages) > 1:
            base_cmd.extend([
                "--db-cluster",
                database_path
            ])

            # Add languages
            for lang in languages:
                base_cmd.extend(["--language", lang])

                # Add language-specific build command if needed
                lang_config = get_language_build_config(lang, repo_path)
                if lang_config.get("needs_build"):
                    base_cmd.extend(["--command", lang_config["command"]])

            # Add --no-run-unnecessary-builds flag
            # base_cmd.append("--no-run-unnecessary-builds")

            logger.info(f"Creating multi-language database at: {database_path}")
            logger.info(f"Languages: {', '.join(languages)}")

        else:
            # Single language database
            lang = languages[0]
            base_cmd.append(database_path)
            base_cmd.extend(["--language", lang])

            # Add language-specific build command if needed
            lang_config = get_language_build_config(lang, repo_path)
            if lang_config.get("needs_build"):
                base_cmd.extend(["--command", lang_config["command"]])
            else:
                base_cmd.append("--no-run-unnecessary-builds")

            logger.info(f"Creating {lang} database at: {database_path}")

        logger.info(f"Running command: {' '.join(base_cmd)}")

        # Run the command
        process = subprocess.run(
            base_cmd,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info("Database creation successful")
        logger.debug(f"Command output: {process.stdout}")

        return database_path

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create CodeQL database: {str(e)}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating database: {str(e)}")
        return None

def process_repository(
        repo_config: dict,
        output_dir: str,
        logger: logging.Logger
) -> bool:
    """Process a single repository to create its CodeQL database"""
    try:
        # Extract repository details
        repo_url = repo_config['url']
        repo_name = repo_url.split('/')[-1].replace('.git', '')

        # Set repository path
        repo_path = os.path.join("./workspace", repo_name)

        if not os.path.exists(repo_path):
            logger.error(f"Repository not found at {repo_path}. Please clone it first.")
            return False

        logger.info(f"Processing repository: {repo_name}")

        # Create the database
        database_path = create_codeql_database(
            repo_path=repo_path,
            database_name=repo_name,
            output_dir=output_dir,
            languages=repo_config.get('languages', ["python"]),
            logger=logger
        )

        if database_path:
            logger.info(f"CodeQL database created successfully for {repo_name}")
            return True
        else:
            logger.error(f"Failed to create CodeQL database for {repo_name}")
            return False

    except Exception as e:
        logger.error(f"Error processing repository {repo_name}: {str(e)}")
        return False

def main():
    try:
        # Load configuration
        config_path = os.path.join(project_root, 'config', 'config.yaml')
        config = load_config(config_path)

        # Setup logging
        logger = setup_logging(config['output']['log_dir'])

        # Get output directory from config
        output_dir = config['output']['results_dir']

        # Process each repository from config
        success_count = 0
        total_repos = len(config['repositories'])

        logger.info(f"Starting database creation for {total_repos} repositories")

        for repo_config in config['repositories']:
            if process_repository(repo_config, output_dir, logger):
                success_count += 1

        logger.info(f"Database creation completed. Success: {success_count}/{total_repos}")

        if success_count < total_repos:
            sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 