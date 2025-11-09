# websocket_manager.py
"""
WebSocket Connection Manager for Sales Chatbot
"""

import logging
from typing import Optional, Dict
from fastapi import WebSocket

from chabot import ConversationMemory, ProfessionalSalesAI
from data_processor import DataProcessor, SalesVectorDB, GEMINI_API_KEY, CHROMA_PERSIST_DIR, MEMORY_STORAGE_DIR, CSV_DATA_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and AI instances"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.ai_instances: Dict[str, ProfessionalSalesAI] = {}
        self.vector_db: Optional[SalesVectorDB] = None
        self.memory_manager: Optional[ConversationMemory] = None
        
        # Initialize system
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize vector database and load data"""
        try:
            logger.info("=" * 70)
            logger.info("🚀 INITIALIZING SALES EXPERIENCE CHATBOT SYSTEM")
            logger.info("=" * 70)
            
            # Initialize vector database
            logger.info("🔧 Initializing ChromaDB...")
            self.vector_db = SalesVectorDB(
                GEMINI_API_KEY,
                CHROMA_PERSIST_DIR
            )
            
            # Initialize memory manager
            logger.info("💾 Initializing Conversation Memory...")
            self.memory_manager = ConversationMemory(MEMORY_STORAGE_DIR)
            
            # Check if data needs to be loaded
            stats = self.vector_db.get_collection_stats()
            
            if stats['total_documents'] == 0:
                logger.info("📊 No data found. Loading and processing CSV...")
                
                # Load and process data
                processor = DataProcessor()
                df = processor.load_csv(CSV_DATA_PATH)
                experiences = processor.process_dataframe(df)
                
                # Add to vector database
                self.vector_db.add_experiences(experiences)
                
                logger.info("✅ Data successfully loaded into ChromaDB")
            else:
                logger.info(f"✅ Found {stats['total_documents']} experiences in ChromaDB")
            
            logger.info("=" * 70)
            logger.info("🎉 SYSTEM READY")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect client and initialize AI brain"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Initialize AI brain for this client
        if client_id not in self.ai_instances:
            self.ai_instances[client_id] = ProfessionalSalesAI(
                GEMINI_API_KEY,
                self.vector_db,
                self.memory_manager,
                client_id
            )
        
        logger.info(f"✅ Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Disconnect client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Keep AI instance for memory persistence
        logger.info(f"🔌 Client {client_id} disconnected")
    
    async def send_message(self, client_id: str, message: dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"⚠️ Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    def get_ai_brain(self, client_id: str) -> Optional[ProfessionalSalesAI]:
        """Get AI brain instance for client"""
        return self.ai_instances.get(client_id)
    
    def clear_client_memory(self, client_id: str):
        """Clear conversation memory for a client"""
        if client_id in self.ai_instances:
            self.ai_instances[client_id].clear_conversation_memory()
            logger.info(f"🗑️ Cleared memory for client {client_id}")
    
    def get_client_stats(self, client_id: str) -> Dict:
        """Get conversation statistics for a client"""
        if client_id in self.ai_instances:
            return self.ai_instances[client_id].get_conversation_stats()
        return {}


# Initialize global manager
manager = ConnectionManager()