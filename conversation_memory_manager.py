# ==================== CONVERSATION MEMORY MANAGER ====================

from datetime import datetime
import hashlib
import logging
from pathlib import Path
import pickle
from typing import Dict
from data_processor import MEMORY_STORAGE_DIR


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages persistent conversation memory for each client"""
    
    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or MEMORY_STORAGE_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Conversation Memory initialized at {self.storage_dir}")
    
    def get_memory_filepath(self, client_id: str) -> Path:
        """Get filepath for client's memory"""
        safe_id = hashlib.md5(client_id.encode()).hexdigest()[:16]
        return self.storage_dir / f"memory_{safe_id}.pkl"
    
    def save_conversation(self, client_id: str, conversation_data: Dict):
        """Save entire conversation history for client"""
        try:
            memory_file = self.get_memory_filepath(client_id)
            
            # Add metadata
            conversation_data['_metadata'] = {
                'last_updated': datetime.now().isoformat(),
                'client_id': client_id,
                'total_exchanges': len(conversation_data.get('history', [])),
                'session_count': conversation_data.get('session_count', 0) + 1
            }
            
            with open(memory_file, 'wb') as f:
                pickle.dump(conversation_data, f)
            
            logger.info(f"Saved conversation memory for {client_id}")
            
        except Exception as e:
            logger.error(f" Error saving memory for {client_id}: {e}")
    
    def load_conversation(self, client_id: str) -> Dict:
        """Load conversation history for client"""
        try:
            memory_file = self.get_memory_filepath(client_id)
            
            if memory_file.exists():
                with open(memory_file, 'rb') as f:
                    conversation_data = pickle.load(f)
                
                logger.info(f" Loaded conversation memory for {client_id}")
                return conversation_data
            else:
                # Return default structure for new client
                return self._get_default_conversation_data()
                
        except Exception as e:
            logger.error(f"Error loading memory for {client_id}: {e}")
            # Return default on error
            return self._get_default_conversation_data()
    
    def _get_default_conversation_data(self) -> Dict:
        """Get default conversation data structure"""
        return {
            'history': [],
            'user_profile': {
                'interests': [],
                'budget_range': '',
                'preferred_locations': [],
                'mentioned_preferences': [],
                'conversation_style': 'professional',
                'conversation_stage': 'initial'
            },
            'session_count': 0,
            'first_interaction': datetime.now().isoformat(),
            'last_interaction': datetime.now().isoformat(),
            'total_messages': 0,
            'previously_discussed_experiences': []
        }
    
    def delete_conversation(self, client_id: str):
        """Delete conversation history for client"""
        try:
            memory_file = self.get_memory_filepath(client_id)
            if memory_file.exists():
                memory_file.unlink()
                logger.info(f"🗑️ Deleted conversation memory for {client_id}")
        except Exception as e:
            logger.error(f"Error deleting memory for {client_id}: {e}")
    
    def get_conversation_stats(self, client_id: str) -> Dict:
        """Get statistics about conversation history"""
        conversation_data = self.load_conversation(client_id)
        
        return {
            'total_messages': conversation_data.get('total_messages', 0),
            'session_count': conversation_data.get('session_count', 0),
            'first_interaction': conversation_data.get('first_interaction'),
            'last_interaction': conversation_data.get('last_interaction'),
            'previously_discussed': len(conversation_data.get('previously_discussed_experiences', [])),
            'known_interests': len(conversation_data.get('user_profile', {}).get('interests', []))
        }

