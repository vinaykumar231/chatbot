# data_processor.py
"""
Data Processing and Vector Database Management
"""

import logging
import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ==================== CONFIGURATION ====================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_PERSIST_DIR = "./chroma_db"
MEMORY_STORAGE_DIR = "./conversation_memory"
CSV_DATA_PATH = "./experiences_dataset_large.csv"
MAX_RESULTS = 3
GEMINI_MODEL = "gemini-2.0-flash-exp"
MAX_CONVERSATION_HISTORY = 50

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file!")

# Create directories
Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
Path(MEMORY_STORAGE_DIR).mkdir(parents=True, exist_ok=True)


# ==================== DATA PROCESSOR ====================

class DataProcessor:
    def __init__(self):
        logger.info("📊 Sales Data Processor initialized")
    
    def load_csv(self, file_path: str) -> pd.DataFrame:
        try:
            logger.info(f"📂 Loading experiences database from {file_path}")
            df = pd.read_csv(file_path)
            
            required_columns = ['id', 'title', 'description', 'category', 'location', 'budget']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            df = df.dropna(subset=['title', 'description'])
            df = df.drop_duplicates(subset=['id'])
            
            logger.info(f"✅ Successfully loaded {len(df)} premium experiences")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error loading CSV: {e}")
            raise
    
    def process_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        all_experiences = []
        
        logger.info(f"🔄 Processing {len(df)} experiences for sales recommendations...")
        
        for idx, row in df.iterrows():
            try:
                experience = {
                    'id': str(row['id']),
                    'title': str(row['title']),
                    'description': str(row['description']),
                    'category': str(row['category']),
                    'location': str(row['location']),
                    'budget': str(row['budget']),
                    'source_row': int(idx)
                }
                all_experiences.append(experience)
                
            except Exception as e:
                logger.error(f"❌ Error processing row {idx}: {e}")
                continue
        
        logger.info(f"✅ Total experiences processed: {len(all_experiences)}")
        return all_experiences


# ==================== SALES VECTOR DATABASE ====================

class SalesVectorDB:
    def __init__(self, api_key: str = None, persist_directory: str = None):
        """
        Initialize Sales Vector Database with Sentence Transformers
        
        Args:
            api_key: Not used anymore (kept for backward compatibility)
            persist_directory: Directory to store ChromaDB data
        """
        self.persist_directory = persist_directory or CHROMA_PERSIST_DIR
        self.collection_name = "sales_experiences"
        
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔧 Initializing Sales Database at {self.persist_directory}")
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Use Sentence Transformer for embeddings (local, free, fast)
        logger.info("🤖 Loading Sentence Transformer model: all-MiniLM-L6-v2")
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # Fast, efficient, and free
        )
        
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"✅ Loaded existing sales collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"✅ Created new sales collection: {self.collection_name}")
    
    def add_experiences(self, experiences: List[Dict]):
        try:
            logger.info(f"📥 Adding {len(experiences)} experiences to sales database...")
            
            documents = []
            metadatas = []
            ids = []
            
            for exp in experiences:
                document_text = f"""
                Title: {exp['title']}
                Category: {exp['category']}
                Location: {exp['location']}
                Budget: {exp['budget']}
                Description: {exp['description']}
                """.strip()
                
                documents.append(document_text)
                metadatas.append(exp)
                ids.append(f"exp_{exp['id']}")
            
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"🎉 Successfully added {len(experiences)} experiences to sales database")
            
        except Exception as e:
            logger.error(f"❌ Error adding experiences: {e}")
            raise
    
    def search_experiences(self, query: str, n_results: int = 5) -> List[Dict]:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            formatted_results = []
            
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else 0.0,
                        'similarity_score': round((1 - results['distances'][0][i]) * 100, 2) if 'distances' in results else 0
                    })
            
            logger.info(f"🔍 Sales search found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Sales search error: {e}")
            return []
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection_name
            }
        except Exception as e:
            logger.error(f"❌ Error getting collection stats: {e}")
            return {'total_documents': 0, 'collection_name': self.collection_name}