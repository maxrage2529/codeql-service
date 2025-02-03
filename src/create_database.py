import os
import sys
import subprocess
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils import setup_logging, load_config

def create_codeql_database(
    repo_path: str,
    database_name: str,
    output_dir: str,
    language: str = "python",
    logger: logging.Logger = None
) -> str:
    """
    Create a CodeQL database for a repository
    
    Args:
        repo_path: Path to the cloned repository
        database_name: Name for the CodeQL database
        output_dir: Directory to store the database
        language: Programming language to analyze
        logger: Logger instance
    
    Returns:
        Path to created database if successful, None otherwise
    """
    if logger is None:
        logger = logging.getLogger('codeql_automation')
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct database path
        database_path = os.path.join(output_dir, f"{database_name}_db")
        
        # Construct the CodeQL command
        cmd = [
            "codeql",
            "database",
            "create",
            database_path,
            f"--language={language}",
            "--source-root",
            repo_path,
            "--overwrite"
        ]
        
        logger.info(f"Creating CodeQL database at: {database_path}")
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Run the command
        process = subprocess.run(
            cmd,
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
            language="python",
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