import json
from pathlib import Path
import pytesseract
from PIL import Image
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import faiss
import numpy as np


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MaritimeContact:
    """Structured data class for maritime contacts matching backend requirements"""
    latitude: Optional[float]
    longitude: Optional[float]
    speed: Optional[float]
    type: str
    timestamp: str
    significance: str
    confidence: float
    description: str
    heading: Optional[float]

    @classmethod
    def from_extracted_data(cls, timestamp: str, coordinates: Optional[Tuple[float, float]], 
                          vessel_type: str, heading: Optional[float], speed: Optional[float],
                          description: str, confidence: float) -> 'MaritimeContact':
        """Factory method to create MaritimeContact from extracted data"""
        return cls(
            latitude=coordinates[0] if coordinates else None,
            longitude=coordinates[1] if coordinates else None,
            speed=speed,
            type=vessel_type,
            timestamp=timestamp,
            significance='routine' if confidence > 0.7 else 'suspicious',
            confidence=confidence,
            description=description,
            heading=heading
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary format matching backend requirements"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'speed': self.speed if self.speed is not None else 0,
            'type': self.type,
            'timestamp': self.timestamp,
            'significance': self.significance,
            'confidence': self.confidence,
            'description': self.description,
            'heading': self.heading
        }
        
        
class MaritimeTextProcessor:
    def __init__(self, model_dir: str = "/home/systemx86/Desktop/Hack/naval/code/rag/maritime_rag"):
        """Initialize the text processor with trained RAG model"""
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory {model_dir} not found")

      
        logger.info("Loading trained models and artifacts...")
        self._load_trained_models()
        
        self.ocr = pytesseract.pytesseract
        logger.info("Text processor initialized successfully")

    def _load_trained_models(self):
        """Load trained models and artifacts"""
       
        with open(self.model_dir / "config.json", 'r') as f:
            self.config = json.load(f)

       
        self.embedding_model = SentenceTransformer(self.config['embedding_model'])
        self.tokenizer = AutoTokenizer.from_pretrained(self.config['generator_model'])
        self.generator = AutoModelForSeq2SeqLM.from_pretrained(self.config['generator_model'])

        
        self.index = faiss.read_index(str(self.model_dir / "maritime.index"))

        
        with open(self.model_dir / "documents.json", 'r') as f:
            self.documents = json.load(f)

    def process_image(self, image_path: str) -> str:
        """Process image through OCR"""
        logger.info(f"Processing image: {image_path}")
        try:
            image = Image.open(image_path)
            text = self.ocr.image_to_string(image)
            logger.info("OCR processing successful")
            return text
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

    def process_report(self, report_path: str) -> List[MaritimeContact]:
        """Process a report file and return structured maritime contacts"""
        logger.info(f"Processing report: {report_path}")
        
        try:
            
            if report_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
                text = self.process_image(report_path)
            else:
                with open(report_path, 'r') as f:
                    text = f.read()
            
           
            contacts = self.extract_maritime_info(text)
            
           
            self._print_contacts(contacts)
            
            return contacts
            
        except Exception as e:
            logger.error(f"Error processing report: {str(e)}")
            raise

    def _print_contacts(self, contacts: List[MaritimeContact]):
        """Print formatted contact information"""
        print("\n=== Extracted Maritime Contacts ===")
        for i, contact in enumerate(contacts, 1):
            print(f"\nContact {i}")
            print(json.dumps(contact.to_dict(), indent=2))
            print("-" * 50)

    

    def _extract_speed(self, text: str) -> Optional[float]:
        """Extract speed information from text"""
        speed_pattern = r'(\d+\.?\d*)\s*knots'
        match = re.search(speed_pattern, text.lower())
        return float(match.group(1)) if match else None

    def _extract_heading(self, text: str) -> Optional[float]:
        """Extract heading information from text"""
        
        compass_dirs = {
            'north': 0, 'northeast': 45, 'east': 90, 'southeast': 135,
            'south': 180, 'southwest': 225, 'west': 270, 'northwest': 315
        }
        
        for direction, degrees in compass_dirs.items():
            if direction in text.lower():
                return float(degrees)
                
       
        degree_pattern = r'(\d+\.?\d*)\s*degrees'
        match = re.search(degree_pattern, text.lower())
        return float(match.group(1)) if match else None

    def _extract_coordinates(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract latitude and longitude from text with support for various formats"""
        
        deg_min_pattern = r"(\d+)°(\d+)'([NSns]),\s*(\d+)°(\d+)'([EWew])"
        match = re.search(deg_min_pattern, text)
        if match:
            lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir = match.groups()
            lat = float(lat_deg) + float(lat_min)/60
            lon = float(lon_deg) + float(lon_min)/60
            if lat_dir.upper() == 'S':
                lat = -lat
            if lon_dir.upper() == 'W':
                lon = -lon
            return (lat, lon)

        
        coord_pattern = r'latitude\s*(-?\d+\.?\d*)\s*[NSns],\s*longitude\s*(-?\d+\.?\d*)\s*[EWew]'
        match = re.search(coord_pattern, text.lower())
        if match:
            lat = float(match.group(1))
            lon = float(match.group(2))
            return (lat, lon)

        return None

    def _calculate_confidence(self, coordinates: Optional[Tuple[float, float]], 
                            speed: Optional[float], 
                            heading: Optional[float], 
                            vessel_type: str) -> float:
        """Calculate confidence score based on extracted information completeness"""
        score = 0.0
        if coordinates:
            score += 0.3
        if speed:
            score += 0.2
        if heading:
            score += 0.2
        if vessel_type and vessel_type != "unknown":
            score += 0.3
        return min(score, 1.0)  

    def extract_maritime_info(self, text: str) -> List[MaritimeContact]:
        """Extract structured maritime information using RAG"""
        logger.info("Extracting maritime information from text")
        
        
        query_embedding = self.embedding_model.encode([text], convert_to_tensor=True)
        query_embedding_np = query_embedding.cpu().numpy()

       
        k = 3
        distances, indices = self.index.search(query_embedding_np, k)
        
       
        vessel_types = [
           
            'cargo vessel', 'container ship', 'tanker', 'oil tanker', 'crude carrier',
            'cruise ship', 'passenger ship',
            
            
            'fishing vessel', 'fishing fleet', 'fishing boat',
            
            
            'patrol vessel', 'patrol boat', 'submarine', 'naval vessel',
            
            
            'pleasure yacht', 'yacht', 'sailing yacht',
            
            
            'research ship', 'research vessel',
            
            
            'suspicious vessel', 'unidentified vessel', 'unidentified craft',
            'unlit vessel', 'fast-moving craft', 'small craft',
            
            
            'pacific trader', 'ocean star', 'black pearl', 'sea breeze',
            'asian enterprise', 'windseeker', 'global freight', 'shadow runner',
            'lucky star', 'serenity'
        ]
        
        contacts = []
        
        
        report_segments = re.split(r'(?:\d+\.\s+|\n\s*\n)', text)
        
        for segment in report_segments:
            if not segment.strip():
                continue
                
            
            coordinates = self._extract_coordinates(segment)
            
            # Extract speed - enhanced pattern
            speed_pattern = r'(\d+\.?\d*)\s*(?:knots?|kts?)'
            speed_match = re.search(speed_pattern, segment.lower())
            speed = float(speed_match.group(1)) if speed_match else None
            
           
            detected_type = 'unknown'
            longest_match = ''
            
            for vtype in vessel_types:
                if vtype.lower() in segment.lower():
                    if len(vtype) > len(longest_match):
                        longest_match = vtype
                        detected_type = vtype
            
            
            if 'multiple' in segment.lower() and 'vessels' in segment.lower():
                detected_type = 'multiple vessels'
                
            
            heading_patterns = {
                r'heading\s+(\d+\.?\d*)\s*(?:degrees|°)': lambda x: float(x),
                r'bearing\s+(\d+\.?\d*)\s*(?:degrees|°)': lambda x: float(x),
                r'moving\s+(north|south|east|west|northeast|northwest|southeast|southwest)': 
                    lambda x: {'north': 0, 'northeast': 45, 'east': 90, 'southeast': 135,
                            'south': 180, 'southwest': 225, 'west': 270, 'northwest': 315}[x.lower()]
            }
            
            heading = None
            for pattern, converter in heading_patterns.items():
                match = re.search(pattern, segment.lower())
                if match:
                    heading = converter(match.group(1))
                    break
            
            
            context = []
            if 'illegal' in segment.lower():
                context.append('illegal activity suspected')
            if 'suspicious' in segment.lower():
                context.append('suspicious behavior')
            if 'routine' in segment.lower():
                context.append('routine transit')
            if 'distress' in segment.lower():
                context.append('vessel in distress')
                
           
            confidence = self._calculate_confidence(coordinates, speed, heading, detected_type)
            
            # Prepare description
            description = segment.strip()
            if context:
                description = f"{description} [Context: {', '.join(context)}]"
            
            
            significance = 'routine'
            if any(c in ['illegal activity suspected', 'suspicious behavior'] for c in context):
                significance = 'suspicious'
            elif 'vessel in distress' in context:
                significance = 'emergency'
            elif confidence < 0.5:
                significance = 'uncertain'
            
            
            contact = MaritimeContact.from_extracted_data(
                timestamp=datetime.now().isoformat(),
                coordinates=coordinates,
                vessel_type=detected_type,
                heading=heading,
                speed=speed,
                description=description,
                confidence=confidence
            )
            
            contacts.append(contact)
        
        logger.info(f"Extracted {len(contacts)} contacts from text")
        return contacts

    def _print_contacts(self, contacts: List[MaritimeContact]):
        """Print formatted contact information"""
        print("\n=== Extracted Maritime Contacts ===")
        try:
            for i, contact in enumerate(contacts, 1):
                print(f"\nContact {i}")
                
                contact_dict = contact.to_dict()
                print(json.dumps(contact_dict, indent=2))
                print("-" * 50)
        except Exception as e:
            logger.error(f"Error printing contacts: {str(e)}")


def main():
    
    processor = MaritimeTextProcessor()
    
    
    example_text = """At 05.30 UTC, an unidentified vessel was sighted at latitude 12.34 N,
    longitude 45.67 E, moving at 12 knots towards the northeast."""
    
    
    contacts = processor.extract_maritime_info(example_text)
    
    
    processor._print_contacts(contacts)

if __name__ == "__main__":
    main()