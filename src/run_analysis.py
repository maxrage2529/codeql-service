import os
import sys
import subprocess
import logging
from typing import Optional

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.utils import setup_logging, load_config

def run_analysis(
    database_path: str,
    output_dir: str,
    query_suite: str,
    logger: logging.Logger = None
) -> Optional[str]:
    """
    Run CodeQL analysis on the specified database
    """
    if logger is None:
        logger = logging.getLogger('codeql_automation')
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get repository name from database path
        repo_name = os.path.basename(database_path).replace('_db', '')
        
        # Construct output file path with repository name
        results_file = os.path.join(output_dir, f"{repo_name}_analysis.sarif")
        
        # Construct the analysis command
        cmd = [
            "codeql",
            "database",
            "analyze",
            database_path,
            query_suite,
            "--format=sarif-latest",
            "--output",
            results_file,
            "--threads=0"
        ]
        
        logger.info(f"Running CodeQL analysis on database: {database_path}")
        logger.info(f"Using query suite: {query_suite}")
        logger.info(f"Results will be saved to: {results_file}")
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Run the analysis
        process = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info("Analysis completed successfully")
        return results_file
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run CodeQL analysis: {str(e)}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {str(e)}")
        return None

def process_repository(
    repo_config: dict,
    output_dir: str,
    query_suite: str,
    logger: logging.Logger
) -> bool:
    """Process a single repository analysis"""
    try:
        repo_url = repo_config['url']
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        # Construct database path
        database_path = os.path.join(output_dir, f"{repo_name}_db")
        
        if not os.path.exists(database_path):
            logger.error(f"Database not found at {database_path}. Please create it first.")
            return False
            
        logger.info(f"Processing analysis for repository: {repo_name}")
        
        # Create analysis directory if it doesn't exist
        analysis_dir = os.path.join(output_dir, "analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        
        # Run the analysis
        results_file = run_analysis(
            database_path=database_path,
            output_dir=analysis_dir,
            query_suite=query_suite,
            logger=logger
        )
        
        if results_file and os.path.exists(results_file):
            logger.info(f"Analysis results saved to: {results_file}")
            
            # Parse and display results count
            try:
                import json
                with open(results_file, 'r') as f:
                    sarif_data = json.load(f)
                    results_count = sum(len(run.get('results', [])) 
                                     for run in sarif_data.get('runs', []))
                    logger.info(f"Found {results_count} issues in {repo_name}")
            except Exception as e:
                logger.error(f"Failed to parse results file: {str(e)}")
            
            return True
        else:
            logger.error(f"Analysis failed for {repo_name}")
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
        
        # Configuration
        output_dir = config['output']['results_dir']
        query_suite = "python-security-and-quality.qls"
        
        # Process each repository from config
        success_count = 0
        total_repos = len(config['repositories'])
        
        logger.info(f"Starting analysis for {total_repos} repositories")
        
        for repo_config in config['repositories']:
            if process_repository(
                repo_config=repo_config,
                output_dir=output_dir,
                query_suite=query_suite,
                logger=logger
            ):
                success_count += 1
        
        logger.info(f"Analysis completed. Success: {success_count}/{total_repos}")
        
        if success_count < total_repos:
            sys.exit(1)
            
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 