# train_maritime_rag.py
import json
from pathlib import Path
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # Fixed import
import logging
import pickle
from tqdm import tqdm


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MaritimeRAGTrainer:
    def __init__(self, output_dir: str = "/kaggle/working/maritime_rag"):
        """Initialize the RAG training system"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
     
        logger.info("Loading models...")
        self.embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        self.tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
        
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        self.documents = []

    def _prepare_text(self, doc):
        """Prepare document text for embedding"""
        fields = []
        if 'text' in doc:
            fields.append(doc['text'])
        if 'metadata' in doc:
            for key, value in doc['metadata'].items():
                fields.append(f"{key}: {value}")
        return " ".join(fields)

    def process_documents(self, documents):
        """Process and index documents"""
        logger.info(f"Processing {len(documents)} documents...")
        
        
        texts = [self._prepare_text(doc) for doc in documents]
        
        # Generate embeddings in batches  batch_size = 32
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embedding_model.encode(
                batch_texts, 
                convert_to_tensor=True, 
                show_progress_bar=False
            )
            embeddings.append(batch_embeddings.cpu().numpy())
        
        embeddings_np = np.vstack(embeddings)
        
        self.index.add(embeddings_np)
        self.documents.extend(documents)
        
        logger.info("Document processing complete")

    def save_artifacts(self):
        """Save all necessary artifacts"""
        logger.info(f"Saving artifacts to {self.output_dir}")
        
        
        faiss.write_index(self.index, str(self.output_dir / "maritime.index"))
     
        with open(self.output_dir / "documents.json", 'w') as f:
            json.dump(self.documents, f)
        
        config = {
            'embedding_model': "BAAI/bge-small-en-v1.5",
            'generator_model': "google/flan-t5-small",
            'embedding_dim': self.embedding_dim
        }
        
        with open(self.output_dir / "config.json", 'w') as f:
            json.dump(config, f)
        
        logger.info("Artifacts saved successfully")

def main():
   
    data_path = Path("/kaggle/working/parsed_maritime_data.json")
    output_dir = Path("/kaggle/working/maritime_rag")
    
   
    logger.info(f"Loading data from {data_path}")
    with open(data_path, 'r') as f:
        documents = json.load(f)
    
    
    trainer = MaritimeRAGTrainer(output_dir=str(output_dir))
    trainer.process_documents(documents)
    trainer.save_artifacts()
    
    logger.info("Training complete!")

if __name__ == "__main__":
    main()