import os
import sys
import logging
from typing import Optional, List

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils import setup_logging, load_config
from src.repository_handler import RepositoryHandler
from src.create_database import create_codeql_database
from src.run_analysis import run_analysis

def process_repository(
        repo_config: dict,
        output_dir: str,
        logger: logging.Logger,
        query_suites: dict
) -> bool:
    """
    Process a single repository through all stages using RepositoryHandler
    """
    try:
        repo_url = repo_config['url']
        branch = repo_config['branch']
        languages = repo_config['languages']
        repo_id = f"{repo_url.split('/')[-1].replace('.git', '')}_{branch}"
        work_dir = os.path.join("./workspace", repo_id)

        logger.info(f"Starting pipeline for repository: {repo_id}")
        logger.info(f"Languages to analyze: {', '.join(languages)}")

        # Initialize repository handler
        repo_handler = RepositoryHandler(work_dir, logger)

        # Step 1: Clone Repository
        logger.info("Step 1: Cloning repository")
        if not repo_handler.clone_repository(repo_url, branch):
            logger.error("Repository cloning failed")
            return False

        # Step 2: Create CodeQL Database
        logger.info("Step 2: Creating CodeQL database")
        database_path = create_codeql_database(
            repo_path=work_dir,
            database_name=repo_id,
            output_dir=output_dir,
            languages=languages,
            logger=logger
        )

        if not database_path:
            logger.error("Database creation failed")
            return False

        # Step 3: Run Analysis for each language
        logger.info("Step 3: Running CodeQL analysis")
        analysis_dir = os.path.join(output_dir, "analysis")

        analysis_success = True
        for lang in languages:
            results_file = run_analysis(
                database_path=database_path,
                output_dir=analysis_dir,
                repo_id=repo_id,
                language=lang,
                query_suites=query_suites,
                logger=logger
            )

            if not results_file:
                logger.error(f"Analysis failed for language: {lang}")
                analysis_success = False

        if not analysis_success:
            return False

        logger.info(f"Successfully completed all steps for {repo_id}")
        return True

        # Cleanup commented out
        # finally:
        #     repo_handler.cleanup()

    except Exception as e:
        logger.error(f"Error processing repository {repo_id}: {str(e)}")
        return False

def main():
    try:
        # Load configuration
        config_path = os.path.join(project_root, 'config', 'config.yaml')
        config = load_config(config_path)

        # Setup logging
        logger = setup_logging(config['output']['log_dir'])

        # Configuration
        output_dir = config['output']['results_dir']
        query_suites = config['codeql']['default_query_suites']

        # Create necessary directories
        os.makedirs("./workspace", exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Process each repository from config
        success_count = 0
        total_repos = len(config['repositories'])

        logger.info(f"Starting pipeline for {total_repos} repositories")

        for repo_config in config['repositories']:
            if process_repository(
                    repo_config=repo_config,
                    output_dir=output_dir,
                    logger=logger,
                    query_suites=query_suites
            ):
                success_count += 1

        logger.info(f"Pipeline completed. Success: {success_count}/{total_repos}")

        if success_count < total_repos:
            sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()