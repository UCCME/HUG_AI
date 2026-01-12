"""
Data processing module for the AI Headhunter system
Handles candidate data parsing, cleaning, and enrichment
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Handles processing of candidate data from various sources
    """
    
    def __init__(self):
        self.config = Config
        logger.info("DataProcessor initialized")
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text data
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-\.,!?;:()\[\]{}@#$%^&*+=<>]', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """
        Extract skills from text using keyword matching
        In a real implementation, this would use NLP techniques
        """
        # Common tech skills list (simplified for this example)
        tech_skills = [
            'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'Go', 'Rust',
            'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask',
            'Machine Learning', 'Deep Learning', 'AI', 'NLP', 'Computer Vision',
            'TensorFlow', 'PyTorch', 'Keras', 'Pandas', 'NumPy', 'SQL',
            'MongoDB', 'PostgreSQL', 'MySQL', 'AWS', 'Azure', 'GCP',
            'Docker', 'Kubernetes', 'CI/CD', 'Git', 'Agile', 'Scrum',
            'Data Science', 'Big Data', 'Hadoop', 'Spark', 'Statistics',
            'UX', 'UI', 'Figma', 'Photoshop', 'Illustrator'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def parse_candidate_from_json(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and clean candidate data from raw JSON
        """
        try:
            candidate = {
                'name': self.clean_text(raw_data.get('name', '')),
                'email': raw_data.get('email', '').strip().lower(),
                'phone': raw_data.get('phone', ''),
                'location': self.clean_text(raw_data.get('location', '')),
                'experience': raw_data.get('experience', 0),
                'education': self.clean_text(raw_data.get('education', '')),
                'summary': self.clean_text(raw_data.get('summary', '')),
                'skills': [],
                'profile_url': raw_data.get('profile_url', ''),
                'current_position': self.clean_text(raw_data.get('current_position', '')),
                'company': self.clean_text(raw_data.get('company', '')),
                'industry': self.clean_text(raw_data.get('industry', ''))
            }
            
            # Extract skills from summary and other text fields if not provided
            if not raw_data.get('skills'):
                text_for_skills = f"{candidate['summary']} {candidate['current_position']} {candidate['education']}"
                candidate['skills'] = self.extract_skills_from_text(text_for_skills)
            else:
                candidate['skills'] = [self.clean_text(skill) for skill in raw_data.get('skills', [])]
            
            # Validate required fields
            if not candidate['name']:
                logger.warning("Candidate missing name, skipping")
                return None
            
            return candidate
            
        except Exception as e:
            logger.error(f"Error parsing candidate data: {str(e)}")
            return None
    
    def process_candidates_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process candidates from a JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            processed_candidates = []
            
            for item in raw_data:
                processed = self.parse_candidate_from_json(item)
                if processed:
                    processed_candidates.append(processed)
            
            logger.info(f"Processed {len(processed_candidates)} candidates from {file_path}")
            return processed_candidates
            
        except Exception as e:
            logger.error(f"Error processing candidates from file {file_path}: {str(e)}")
            return []
    
    def enrich_candidate_data(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich candidate data with additional information
        """
        enriched = candidate.copy()
        
        # Add timestamp of processing
        enriched['processed_at'] = datetime.now().isoformat()
        
        # Calculate experience level based on years
        exp = candidate.get('experience', 0)
        if exp >= 10:
            enriched['experience_level'] = 'Senior'
        elif exp >= 5:
            enriched['experience_level'] = 'Mid-level'
        elif exp >= 2:
            enriched['experience_level'] = 'Junior'
        else:
            enriched['experience_level'] = 'Entry'
        
        # Extract location components (simplified)
        location = candidate.get('location', '')
        if location:
            parts = location.split(', ')
            if len(parts) >= 1:
                enriched['city'] = parts[0]
            if len(parts) >= 2:
                enriched['state'] = parts[1]
            if len(parts) >= 3:
                enriched['country'] = parts[2]
        
        # Calculate skill count
        enriched['skill_count'] = len(candidate.get('skills', []))
        
        return enriched
    
    def normalize_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a list of candidate dictionaries
        """
        normalized = []
        
        for candidate in candidates:
            enriched = self.enrich_candidate_data(candidate)
            normalized.append(enriched)
        
        logger.info(f"Normalized {len(normalized)} candidates")
        return normalized
    
    def save_processed_data(self, candidates: List[Dict[str, Any]], output_path: str):
        """
        Save processed candidates to a file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(candidates, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(candidates)} processed candidates to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving processed data to {output_path}: {str(e)}")
    
    def filter_candidates(self, candidates: List[Dict[str, Any]], 
                         filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter candidates based on provided criteria
        """
        filtered = candidates
        
        # Filter by location if specified
        if 'location' in filters:
            location = filters['location'].lower()
            filtered = [c for c in filtered 
                       if location in c.get('location', '').lower()]
        
        # Filter by minimum experience if specified
        if 'min_experience' in filters:
            min_exp = filters['min_experience']
            filtered = [c for c in filtered 
                       if c.get('experience', 0) >= min_exp]
        
        # Filter by required skills if specified
        if 'required_skills' in filters:
            req_skills = [s.lower() for s in filters['required_skills']]
            filtered = [c for c in filtered 
                       if all(skill in [s.lower() for s in c.get('skills', [])] 
                             for skill in req_skills)]
        
        # Filter by experience level if specified
        if 'experience_level' in filters:
            exp_level = filters['experience_level']
            filtered = [c for c in filtered 
                       if c.get('experience_level', '') == exp_level]
        
        logger.info(f"Applied filters, {len(filtered)}/{len(candidates)} candidates remain")
        return filtered


def process_sample_data():
    """
    Example function to demonstrate data processing
    """
    processor = DataProcessor()
    
    # Sample raw data
    sample_data = [
        {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "skills": ["Python", "Machine Learning", "TensorFlow"],
            "experience": 7,
            "education": "MSc in Computer Science",
            "location": "San Francisco, CA",
            "summary": "Senior AI engineer with expertise in Python and machine learning. 7+ years of experience building ML models.",
            "profile_url": "https://linkedin.com/in/johndoe"
        },
        {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "skills": ["JavaScript", "React", "Node.js"],
            "experience": 5,
            "education": "BSc in Software Engineering",
            "location": "New York, NY",
            "summary": "Full-stack developer with 5 years of experience. Expert in JavaScript frameworks.",
            "profile_url": "https://linkedin.com/in/janesmith"
        }
    ]
    
    # Process the data
    processed = []
    for item in sample_data:
        result = processor.parse_candidate_from_json(item)
        if result:
            processed.append(result)
    
    # Normalize the data
    normalized = processor.normalize_candidates(processed)
    
    # Print results
    for candidate in normalized:
        print(f"Name: {candidate['name']}")
        print(f"Email: {candidate['email']}")
        print(f"Skills: {', '.join(candidate['skills'])}")
        print(f"Experience: {candidate['experience']} years ({candidate['experience_level']})")
        print(f"Location: {candidate['location']}")
        print(f"Processed at: {candidate['processed_at']}")
        print("-" * 40)


if __name__ == "__main__":
    process_sample_data()