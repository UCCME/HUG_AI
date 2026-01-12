"""
AI Headhunter - Intelligent Talent Acquisition System
Main application module
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Candidate:
    """
    Represents a job candidate with skills, experience, and other attributes
    """
    
    def __init__(self, name: str, email: str, skills: List[str], experience: int, 
                 education: str, location: str, profile_url: str = None):
        self.name = name
        self.email = email
        self.skills = skills
        self.experience = experience
        self.education = education
        self.location = location
        self.profile_url = profile_url
        self.score = 0.0  # Calculated match score
        self.summary = ""
        
    def to_dict(self) -> Dict:
        """Convert candidate to dictionary representation"""
        return {
            'name': self.name,
            'email': self.email,
            'skills': self.skills,
            'experience': self.experience,
            'education': self.education,
            'location': self.location,
            'profile_url': self.profile_url,
            'score': self.score,
            'summary': self.summary
        }


class JobDescription:
    """
    Represents a job opening with requirements and preferences
    """
    
    def __init__(self, title: str, description: str, required_skills: List[str], 
                 preferred_skills: List[str], experience_required: int, 
                 location: str, salary_range: str = None):
        self.title = title
        self.description = description
        self.required_skills = required_skills
        self.preferred_skills = preferred_skills
        self.experience_required = experience_required
        self.location = location
        self.salary_range = salary_range


class AIHeadhunter:
    """
    Main class for the AI Headhunter system
    """
    
    def __init__(self):
        self.candidates: List[Candidate] = []
        self.job_descriptions: List[JobDescription] = []
        logger.info("AI Headhunter system initialized")
    
    def load_candidates(self, source_file: str) -> bool:
        """
        Load candidates from a data source (file, API, etc.)
        """
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                candidate = Candidate(
                    name=item.get('name', ''),
                    email=item.get('email', ''),
                    skills=item.get('skills', []),
                    experience=item.get('experience', 0),
                    education=item.get('education', ''),
                    location=item.get('location', ''),
                    profile_url=item.get('profile_url', '')
                )
                self.candidates.append(candidate)
                
            logger.info(f"Loaded {len(self.candidates)} candidates from {source_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading candidates from {source_file}: {str(e)}")
            return False
    
    def add_job_description(self, job: JobDescription):
        """
        Add a job description to the system
        """
        self.job_descriptions.append(job)
        logger.info(f"Added job description: {job.title}")
    
    def calculate_match_score(self, candidate: Candidate, job: JobDescription) -> float:
        """
        Calculate match score between candidate and job requirements
        """
        score = 0.0
        
        # Skills matching (required skills: 50% of score, preferred skills: 30% of score)
        required_match_count = 0
        for skill in job.required_skills:
            if skill.lower() in [s.lower() for s in candidate.skills]:
                required_match_count += 1
        
        if len(job.required_skills) > 0:
            required_score = (required_match_count / len(job.required_skills)) * 0.5
        else:
            required_score = 0.5  # If no required skills, give full score for this part
        
        preferred_match_count = 0
        for skill in job.preferred_skills:
            if skill.lower() in [s.lower() for s in candidate.skills]:
                preferred_match_count += 1
        
        if len(job.preferred_skills) > 0:
            preferred_score = (preferred_match_count / len(job.preferred_skills)) * 0.3
        else:
            preferred_score = 0.0
        
        # Experience matching (20% of score)
        if candidate.experience >= job.experience_required:
            experience_score = 0.2
        else:
            # Partial score if experience is close to requirement
            experience_score = max(0.0, 0.2 * (candidate.experience / max(job.experience_required, 1)))
        
        # Location matching (bonus up to 10%)
        location_score = 0.1 if job.location.lower() in candidate.location.lower() else 0.0
        
        score = required_score + preferred_score + experience_score + location_score
        return min(score, 1.0)  # Cap at 1.0
    
    def rank_candidates(self, job: JobDescription) -> List[Candidate]:
        """
        Rank candidates based on their match score for a specific job
        """
        for candidate in self.candidates:
            candidate.score = self.calculate_match_score(candidate, job)
        
        # Sort candidates by score in descending order
        ranked_candidates = sorted(self.candidates, key=lambda c: c.score, reverse=True)
        
        # Add summary for top candidates
        for candidate in ranked_candidates[:10]:  # Only for top 10
            candidate.summary = self.generate_candidate_summary(candidate, job)
        
        return ranked_candidates
    
    def generate_candidate_summary(self, candidate: Candidate, job: JobDescription) -> str:
        """
        Generate a summary of why this candidate matches the job
        """
        matched_skills = [skill for skill in job.required_skills 
                         if skill.lower() in [s.lower() for s in candidate.skills]]
        matched_preferred_skills = [skill for skill in job.preferred_skills 
                                   if skill.lower() in [s.lower() for s in candidate.skills]]
        
        summary = f"This candidate has {len(matched_skills)}/{len(job.required_skills)} required skills: "
        summary += ", ".join(matched_skills) + ". "
        
        if matched_preferred_skills:
            summary += f"Also has preferred skills: " + ", ".join(matched_preferred_skills) + ". "
        
        if candidate.experience >= job.experience_required:
            summary += f"Has {candidate.experience} years of experience (required: {job.experience_required}). "
        else:
            summary += f"Has {candidate.experience} years of experience (required: {job.experience_required}). "
        
        if job.location.lower() in candidate.location.lower():
            summary += "Located in the required area."
        
        return summary
    
    def save_results(self, candidates: List[Candidate], job_title: str, output_file: str = None):
        """
        Save the ranked candidates to a file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"results_{job_title.replace(' ', '_')}_{timestamp}.json"
        
        results = [candidate.to_dict() for candidate in candidates]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(candidates)} ranked candidates to {output_file}")
        return output_file


def main():
    """
    Main function to demonstrate the AI Headhunter system
    """
    # Initialize the AI Headhunter system
    ai_headhunter = AIHeadhunter()
    
    # Example job description
    job = JobDescription(
        title="Senior AI Engineer",
        description="We are looking for an experienced AI engineer to join our team building innovative AI solutions.",
        required_skills=["Python", "Machine Learning", "TensorFlow", "Deep Learning"],
        preferred_skills=["NLP", "Computer Vision", "PyTorch", "Cloud Computing"],
        experience_required=5,
        location="San Francisco",
        salary_range="$120k - $160k"
    )
    
    ai_headhunter.add_job_description(job)
    
    # Load sample candidates (in a real system, this would come from a database or API)
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
    ranked_candidates = ai_headhunter.rank_candidates(job)
    
    # Print results
    print(f"Ranked candidates for: {job.title}")
    print("=" * 50)
    for i, candidate in enumerate(ranked_candidates, 1):
        print(f"{i}. {candidate.name} - Score: {candidate.score:.2f}")
        print(f"   Skills: {', '.join(candidate.skills)}")
        print(f"   Experience: {candidate.experience} years")
        print(f"   Location: {candidate.location}")
        print(f"   Summary: {candidate.summary}")
        print()
    
    # Save results
    output_file = ai_headhunter.save_results(ranked_candidates, job.title)
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()