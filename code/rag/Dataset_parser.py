import json
from pathlib import Path
import re
from datetime import datetime
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_json_block(block):
    """Parse JSON blocks found in the markdown files."""
    try:
       
        clean_block = re.sub(r'```json\s*|\s*```', '', block).strip()
        if not clean_block:
            logger.warning("Empty JSON block found")
            return None
            
        logger.debug(f"Attempting to parse JSON block: {clean_block[:100]}...")
        return json.loads(clean_block)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}\nBlock content: {clean_block[:200]}...")
        return None

def parse_message_block(block):
    """Parse military-style message blocks."""
    try:
        
        clean_block = re.sub(r'```\s*|\s*```', '', block).strip()
        if not clean_block:
            logger.warning("Empty message block found")
            return None
            
        logger.debug(f"Parsing message block: {clean_block[:100]}...")
        
        
        message_dict = {
            'document_type': 'message',
            'text': clean_block,
            'metadata': {}
        }
        
        
        field_patterns = {
            'from': r'FROM:\s*([^\n]+)',
            'to': r'TO:\s*([^\n]+)',
            'date_time': r'DTG:\s*([^\n]+)',
            'priority': r'PRIORITY:\s*([^\n]+)'
        }
        
       
        for field, pattern in field_patterns.items():
            match = re.search(pattern, clean_block)
            if match:
                message_dict['metadata'][field] = match.group(1).strip()
            else:
                logger.warning(f"Field '{field}' not found in message block")
        
        return message_dict
    except Exception as e:
        logger.error(f"Error parsing message block: {str(e)}\nBlock content: {clean_block[:200]}...")
        return None

def parse_surveillance_log(block):
    """Parse surveillance log entries."""
    try:
        
        clean_block = re.sub(r'```\s*|\s*```', '', block).strip()
        if not clean_block:
            logger.warning("Empty surveillance log found")
            return None
            
        logger.debug(f"Parsing surveillance log: {clean_block[:100]}...")
        
        log_dict = {
            'document_type': 'surveillance_log',
            'text': clean_block,
            'metadata': {}
        }
        
        
        field_patterns = {
            'date': r'Date:\s*([^\n]+)',
            'time': r'Time:\s*([^\n]+)',
            'location': r'Location:\s*([^\n]+)',
            'report': r'Report:\s*([^\n]+)'
        }
        
        
        for field, pattern in field_patterns.items():
            match = re.search(pattern, clean_block)
            if match:
                log_dict['metadata'][field] = match.group(1).strip()
            else:
                logger.warning(f"Field '{field}' not found in surveillance log")
        
        return log_dict
    except Exception as e:
        logger.error(f"Error parsing surveillance log: {str(e)}\nBlock content: {clean_block[:200]}...")
        return None

def parse_markdown_to_json(file_paths):
    """Enhanced parser to handle different types of maritime data formats."""
    documents = []
    total_files = len(file_paths)
    
    logger.info(f"Starting to process {total_files} files")
    
    for idx, file_path in enumerate(file_paths, 1):
        logger.info(f"Processing file {idx}/{total_files}: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                if not content.strip():
                    logger.warning(f"Empty file: {file_path.name}")
                    continue
                
                # Split content into numbered blocks
                # Look for patterns like "1. ```", "2. ```", etc.
                blocks = re.split(r'\n\d+\.\s*(?=```)', content)
                logger.info(f"Found {len(blocks)} blocks in {file_path.name}")
                
                for block_num, block in enumerate(blocks, 1):
                    if not block.strip():
                        continue
                        
                    logger.debug(f"Processing block {block_num} in {file_path.name}")
                    parsed_doc = None
                    
                    # Try parsing as JSON first
                    if 'json' in block.lower():
                        parsed_doc = parse_json_block(block)
                    # Try parsing as military message
                    elif 'FROM:' in block and 'TO:' in block:
                        parsed_doc = parse_message_block(block)
                    # Try parsing as surveillance log
                    elif 'Date:' in block and 'Report:' in block:
                        parsed_doc = parse_surveillance_log(block)
                    
                    if parsed_doc:
                        parsed_doc['source_file'] = file_path.name
                        parsed_doc['block_number'] = block_num
                        documents.append(parsed_doc)
                        logger.debug(f"Successfully parsed block {block_num}")
                    else:
                        logger.warning(f"Failed to parse block {block_num} in {file_path.name}")
                        logger.debug(f"Block content: {block[:200]}...")
                
                logger.info(f"Successfully processed {file_path.name}, found {len([d for d in documents if d['source_file'] == file_path.name])} valid documents")
                
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            continue
    
    logger.info(f"Parsing complete. Total documents processed: {len(documents)}")
    return documents

def main():
    """Main function with enhanced error handling and debugging."""
    try:
        data_dir = Path("/kaggle/input/naval-hack/naval_data")
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        
        file_paths = list(data_dir.glob("*.md"))
        if not file_paths:
            raise FileNotFoundError(f"No markdown files found in {data_dir}")
        
        logger.info(f"Found {len(file_paths)} markdown files to process")
        
       
        parsed_data = parse_markdown_to_json(file_paths)
        
        
        if not parsed_data:
            raise ValueError("No documents were successfully parsed")
        
       
        output_file = Path('/kaggle/working/parsed_maritime_data.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as json_file:
            json.dump(parsed_data, json_file, indent=4, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(parsed_data)} documents to {output_file}")
        
        
        doc_types = {}
        for doc in parsed_data:
            doc_type = doc.get('document_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        logger.info("Document type statistics:")
        for doc_type, count in doc_types.items():
            logger.info(f"  {doc_type}: {count} documents")
            
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()