import os
from dotenv import load_dotenv
from loguru import logger
from typing import List, Dict, Any

from preprocessing.cleaner import TextCleaner
from preprocessing.chunker import TextChunker
from models.embeddings import MiniLMEmbedder
from preprocessing.db_vectors import VectorDBManager

def process_batch(
    raw_docs: List[Dict[str, Any]], 
    cleaner: TextCleaner, 
    chunker: TextChunker, 
    embedder: MiniLMEmbedder
) -> List[Dict[str, Any]]:
    processed_docs = []
    
    # 1. Clean texts
    for doc in raw_docs:
        doc['text_clean'] = cleaner.clean(doc['text'])
        doc['chunks'] = chunker.chunk(doc['text_clean'])
        doc['chunk_count'] = len(doc['chunks'])
    
    # 2. Extract valid texts for embedding
    texts_to_embed = [doc['text_clean'] for doc in raw_docs]
    
    # 3. Generate embeddings in bulk
    embeddings = embedder.embed_batch(texts_to_embed)
    
    # 4. Map back to documents
    for doc, emb in zip(raw_docs, embeddings):
        processed_docs.append({
            'raw_doc_id': doc['id'],
            'source': doc['source'],
            'text_clean': doc['text_clean'],
            'text_original': doc['text'],
            'chunks': doc['chunks'],
            'chunk_count': doc['chunk_count'],
            'embedding': str(emb), # pgvector expects a string representation like '[1,2,3]'
            'embedding_model': embedder.model.__class__.__name__ if hasattr(embedder, 'model') else 'MiniLM',
            'rating': doc['rating'],
            'date': doc['date'],
            'url': doc['url'],
        })
        
    return processed_docs

def main():
    load_dotenv()
    logger.info("Starting Phase 2: Data Preprocessing & Embedding")
    
    cleaner = TextCleaner()
    chunker = TextChunker(chunk_size=512, overlap=50)
    
    logger.info("Loading Embedding Model (MiniLM)...")
    embedder = MiniLMEmbedder()
    
    db = VectorDBManager()
    
    batch_size = 200
    total_processed = 0
    
    while True:
        logger.info(f"Fetching up to {batch_size} unprocessed documents...")
        raw_docs = db.fetch_unprocessed_documents(limit=batch_size)
        
        if not raw_docs:
            logger.info("No more documents to process!")
            break
            
        logger.info(f"Processing batch of {len(raw_docs)} documents...")
        processed_docs = process_batch(raw_docs, cleaner, chunker, embedder)
        
        logger.info(f"Saving {len(processed_docs)} processed documents to vector database...")
        db.save_processed_documents(processed_docs)
        
        total_processed += len(processed_docs)
        logger.success(f"Successfully processed and embedded {total_processed} documents so far.")
        
    logger.info("--- Phase 2 Complete ---")

if __name__ == "__main__":
    main()
