import argparse
from pathlib import Path
from ocr_infer import MaritimeTextProcessor

def process_input(input_path: str) -> None:
    """
    Process either an image or text file containing maritime information.
    
    Args:
        input_path: Path to the input file (can be image or text)
    """
    try:
        
        processor = MaritimeTextProcessor()
        
        file_path = Path(input_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")
            
       
        print(f"\nProcessing file: {input_path}")
        print("=" * 50)
        
        contacts = processor.process_report(str(file_path))
        
        # Print summary
        print(f"\nSummary:")
        print(f"Total contacts detected: {len(contacts)}")
        print(f"Average confidence: {sum(c.confidence for c in contacts)/len(contacts):.2f}")
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise

def main():
    
    parser = argparse.ArgumentParser(description="Process maritime reports from image or text files")
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to input file (supports .txt, .png, .jpg, .jpeg, .tiff)"
    )
    
  
    args = parser.parse_args()
    
    # Process the input process_input(args.input_path)

if __name__ == "__main__":
    main()