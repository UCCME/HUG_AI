"""
Script to run the AI Headhunter system
"""

import argparse
import os
import sys
from typing import List

# Add the project root to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import AIHeadhunter, JobDescription, Candidate
from data_processor import DataProcessor
from config import config, Config


def load_candidates_from_json(filepath: str) -> List[dict]:
    """
    Load candidates from a JSON file using the DataProcessor
    """
    processor = DataProcessor()
    return processor.process_candidates_from_file(filepath)


def run_demo():
    """
    Run a demonstration of the AI Headhunter system
    """
    print("AI Headhunter - Intelligent Talent Acquisition System")
    print("=" * 60)
    
    # Initialize the AI Headhunter system
    ai_headhunter = AIHeadhunter()
    
    # Example job description
    job = JobDescription(
        title="Senior AI Engineer",
        description="We are looking for an experienced AI engineer to join our team building innovative AI solutions. "
                   "The ideal candidate will have experience with machine learning frameworks, deep learning, and NLP.",
        required_skills=["Python", "Machine Learning", "TensorFlow", "Deep Learning"],
        preferred_skills=["NLP", "Computer Vision", "PyTorch", "Cloud Computing", "AWS"],
        experience_required=5,
        location="San Francisco",
        salary_range="$120k - $160k"
    )
    
    ai_headhunter.add_job_description(job)
    
    # Load sample candidates from JSON file
    sample_data_path = os.path.join(os.path.dirname(__file__), "sample_candidates.json")
    if os.path.exists(sample_data_path):
        processed_candidates = load_candidates_from_json(sample_data_path)
        
        # Convert to Candidate objects
        for item in processed_candidates:
            candidate = Candidate(
                name=item['name'],
                email=item['email'],
                skills=item['skills'],
                experience=item['experience'],
                education=item['education'],
                location=item['location'],
                profile_url=item['profile_url']
            )
            ai_headhunter.candidates.append(candidate)
        
        print(f"Loaded {len(ai_headhunter.candidates)} candidates from {sample_data_path}")
    else:
        print(f"Sample data file not found: {sample_data_path}")
        print("Using sample candidates directly in code...")
        
        # Fallback sample candidates
        sample_candidates = [
            {
                "name": "Alex Johnson",
                "email": "alex.johnson@example.com",
                "skills": ["Python", "Machine Learning", "TensorFlow", "Deep Learning", "NLP"],
                "experience": 7,
                "education": "MSc in Computer Science",
                "location": "San Francisco, CA",
                "profile_url": "https://linkedin.com/in/alexjohnson"
            },
            {
                "name": "Maria Garcia",
                "email": "maria.g@example.com",
                "skills": ["Python", "Machine Learning", "PyTorch", "Computer Vision"],
                "experience": 4,
                "education": "BSc in Software Engineering",
                "location": "San Jose, CA",
                "profile_url": "https://linkedin.com/in/mariagarcia"
            },
            {
                "name": "David Chen",
                "email": "david.chen@example.com",
                "skills": ["Python", "Machine Learning", "TensorFlow", "Deep Learning", "NLP", "Cloud Computing"],
                "experience": 8,
                "education": "PhD in Artificial Intelligence",
                "location": "San Francisco, CA",
                "profile_url": "https://linkedin.com/in/davidchen"
            }
        ]
        
        # Add sample candidates to the system
        for item in sample_candidates:
            candidate = Candidate(
                name=item['name'],
                email=item['email'],
                skills=item['skills'],
                experience=item['experience'],
                education=item['education'],
                location=item['location'],
                profile_url=item['profile_url']
            )
            ai_headhunter.candidates.append(candidate)
    
    # Rank candidates for the job
    print(f"\nRanking candidates for: {job.title}")
    print("-" * 60)
    
    ranked_candidates = ai_headhunter.rank_candidates(job)
    
    # Print results
    print(f"Top candidates for: {job.title}")
    print("=" * 60)
    for i, candidate in enumerate(ranked_candidates[:5], 1):  # Show top 5
        print(f"{i}. {candidate.name} - Match Score: {candidate.score:.2f}")
        print(f"   Skills: {', '.join(candidate.skills)}")
        print(f"   Experience: {candidate.experience} years")
        print(f"   Location: {candidate.location}")
        print(f"   Summary: {candidate.summary}")
        print()
    
    # Save results
    output_file = ai_headhunter.save_results(ranked_candidates, job.title)
    print(f"Full results saved to: {output_file}")
    
    return ai_headhunter, job


def main():
    """
    Main function to run the AI Headhunter system
    """
    parser = argparse.ArgumentParser(description='AI Headhunter - Intelligent Talent Acquisition System')
    parser.add_argument('--demo', action='store_true', help='Run a demo of the system')
    parser.add_argument('--config', type=str, default='default', help='Configuration to use')
    
    args = parser.parse_args()
    
    # Validate configuration
    cfg = config.get(args.config, config['default'])
    validation_errors = cfg.validate()
    
    if validation_errors:
        print("Configuration validation errors:")
        for error in validation_errors:
            print(f"  - {error}")
        sys.exit(1)
    
    if args.demo or len(sys.argv) == 1:  # Run demo if no arguments provided
        run_demo()
    else:
        print("AI Headhunter system is ready to run.")
        # In a full implementation, this would start the web API
        # ai_headhunter = AIHeadhunter()
        # ai_headhunter.start_api()


if __name__ == "__main__":
    main()