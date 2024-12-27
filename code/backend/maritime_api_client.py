import requests
import json
import argparse
from typing import List, Union
from pathlib import Path
from ocr_infer import MaritimeTextProcessor, MaritimeContact
from datetime import datetime

class MaritimeAPIClient:
    """Client for sending maritime contact data to the backend API"""
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.process_endpoint = f"{base_url}/process_report/"
        self.processor = MaritimeTextProcessor()

    def process_input(self, input_data: Union[str, Path]) -> List[MaritimeContact]:
        """
        Process different types of input (text string, file path)
        
        Args:
            input_data: Either a text string or a file path
        """
        try:
            
            if isinstance(input_data, (str, Path)) and Path(input_data).exists():
                path = Path(input_data)
                if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tiff']:
                    
                    return self.processor.process_report(str(path))
                else:
                    
                    with open(path, 'r') as f:
                        text = f.read()
                    return self.processor.extract_maritime_info(text)
            else:
                
                return self.processor.extract_maritime_info(str(input_data))
                
        except Exception as e:
            print(f"Error processing input: {str(e)}")
            raise

    def send_to_backend(self, contacts: List[MaritimeContact]) -> dict:
        """Send processed contacts to backend"""
        try:
           
            formatted_data = self._format_contacts_for_backend(contacts)
            
            
            markdown_content = self._create_markdown_content(formatted_data)
            
            files = {
                'file': ('report.md', markdown_content.encode('utf-8'), 'text/markdown')
            }
            
            
            response = requests.post(self.process_endpoint, files=files)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}

    def _format_contacts_for_backend(self, contacts: List[MaritimeContact]) -> List[dict]:
        """Format contacts into the structure expected by the backend"""
        formatted_data = []
        
        for contact in contacts:
            contact_data = {
                "latitude": contact.latitude,
                "longitude": contact.longitude,
                "type": contact.type,
                "significance": contact.significance,
                "speed": contact.speed,
                "timestamp": contact.timestamp
            }
            formatted_data.append(contact_data)
            
        return formatted_data

    def _create_markdown_content(self, formatted_data: List[dict]) -> str:
        """Create markdown content with JSON blocks for each contact"""
        markdown_parts = ["# Maritime Contact Report\n\n"]
        
        for i, contact in enumerate(formatted_data, 1):
            markdown_parts.append(f"## Contact {i}\n\n```json\n{json.dumps(contact, indent=2)}\n```\n\n")
            
        return "".join(markdown_parts)

def process_input(input_data: str, base_url: str = "http://localhost:8000") -> None:
    """Process input and send to backend"""
    print(f"\nProcessing input...")
    print("=" * 50)
    
    client = MaritimeAPIClient(base_url)
    
    try:
        
        contacts = client.process_input(input_data)
        
        
        response = client.send_to_backend(contacts)
        
        if "error" in response:
            print(f"\nError: {response['error']}")
        else:
            print("\nSuccess! Backend Response:")
            print(json.dumps(response, indent=2))
            
    except Exception as e:
        print(f"\nError: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Process maritime data and send to backend")
    
    # Add arguments
    parser.add_argument(
        "-i", "--input",
        help="Input data (file path or text string)",
        type=str
    )
    
    parser.add_argument(
        "--url",
        help="Backend API URL (default: http://localhost:8000)",
        default="http://localhost:8000",
        type=str
    )
    
    args = parser.parse_args()
    
    if args.input:
        
        process_input(args.input, args.url)
    else:
        
        while True:
            print("\nMaritime Contact Processor")
            print("=" * 50)
            print("1. Process a file")
            print("2. Enter text directly")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == "1":
                file_path = input("\nEnter the file path: ")
                if file_path.lower() == 'exit':
                    break
                process_input(file_path, args.url)
                
            elif choice == "2":
                print("\nEnter your text (type 'END' on a new line when finished):")
                lines = []
                while True:
                    line = input()
                    if line == 'END':
                        break
                    lines.append(line)
                text = '\n'.join(lines)
                process_input(text, args.url)
                
            elif choice == "3":
                break
                
            else:
                print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    main()