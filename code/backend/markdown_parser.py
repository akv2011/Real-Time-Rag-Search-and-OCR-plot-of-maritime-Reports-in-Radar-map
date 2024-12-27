import re
import json
from datetime import datetime

def parse_markdown(content):
    
    json_blocks = re.findall(r'```json(.*?)```', content, re.DOTALL)
    
    # Extract structured data from each JSON block
    extracted_data = []
    for block in json_blocks:
        try:
            data = json.loads(block.strip())
            
           
            if 'coordinates' in data:
                latitude = data['coordinates'][0]['lat']
                longitude = data['coordinates'][0]['lon']
            else:
                latitude = data.get('latitude')
                longitude = data.get('longitude')

            structured_data = {
                'latitude': latitude,
                'longitude': longitude,
                'type': data.get('type', data.get('name', 'Unknown Zone')),
                'significance': data.get('significance', 'Not Available'),
                'speed': data.get('speed', 0),
                'timestamp': data.get('timestamp', '2024-10-20T05:30:00Z'),
                'description': data.get('description', ''),
                'heading': data.get('heading'),
                'confidence': data.get('confidence', 1.0)
            }
            extracted_data.append(structured_data)
        except json.JSONDecodeError:
            print("Error parsing JSON block")
        except Exception as e:
            print(f"Error processing contact data: {str(e)}")
    
    return extracted_data