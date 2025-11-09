"""
FastAPI WebSocket Server for Sales Experience Chatbot
"""

import logging
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from websocket_manager import manager

# --------------------------------------------------------
# Logging Configuration
# --------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------
# FastAPI Initialization
# --------------------------------------------------------
app = FastAPI(
    title="Sales Experience Chatbot API",
    description="Professional Sales AI with Conversation Memory",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------
# REST Endpoints
# --------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Sales Experience Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "embedding_model": "all-MiniLM-L6-v2 (Sentence Transformers)"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# --------------------------------------------------------
# WebSocket Endpoint
# --------------------------------------------------------
@app.websocket("/ws/chat/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for chat
    
    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
    """
    await manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await manager.send_message(client_id, {
            "type": "system",
            "message": "Connected to Sales Experience Chatbot! 🎉",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            logger.info(f"📨 Received from {client_id}: {data}")
            
            # Determine message type
            message_type = data.get("type", "chat")
            if message_type == "user_message":
                message_type = "chat"
            
            user_message = data.get("message", "")
            
            # Handle chat messages
            if message_type == "chat" and user_message:
                ai_brain = manager.get_ai_brain(client_id)
                
                if not ai_brain:
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": "AI brain not initialized. Please reconnect."
                    })
                    continue
                
                # Send typing indicator
                await manager.send_message(client_id, {
                    "type": "typing",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Generate AI response
                try:
                    logger.info(f"🤖 Generating response for: {user_message}")
                    
                    # Updated function call (correct method)
                    response_text, experience_data, is_farewell = await ai_brain.detect_intent_and_respond(user_message)
                    
                    logger.info(f"✅ Response generated: {response_text[:100]}...")
                    
                    # Handle farewell separately
                    if is_farewell:
                        await manager.send_message(client_id, {
                            "type": "farewell",
                            "message": response_text,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        await manager.send_message(client_id, {
                            "type": "response",
                            "message": response_text,
                            "experiences": experience_data,
                            "timestamp": datetime.now().isoformat()
                        })
                
                except Exception as e:
                    logger.error(f"❌ Error generating response for {client_id}: {e}", exc_info=True)
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": "Sorry, I encountered an error. Please try again."
                    })
            
            # Handle memory clearing
            elif message_type == "clear_memory":
                manager.clear_client_memory(client_id)
                await manager.send_message(client_id, {
                    "type": "system",
                    "message": "Conversation memory cleared! Starting fresh. 🔄",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Handle conversation stats request
            elif message_type == "get_stats":
                stats = manager.get_client_stats(client_id)
                await manager.send_message(client_id, {
                    "type": "stats",
                    "data": stats,
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"🔌 Client {client_id} disconnected")
    
    except Exception as e:
        logger.error(f"❌ WebSocket error for {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)

# --------------------------------------------------------
# REST Utility Endpoints
# --------------------------------------------------------
@app.get("/api/stats/{client_id}")
async def get_client_stats(client_id: str):
    """Get conversation statistics for a client"""
    stats = manager.get_client_stats(client_id)
    return {
        "client_id": client_id,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/clear_memory/{client_id}")
async def clear_client_memory(client_id: str):
    """Clear conversation memory for a client"""
    manager.clear_client_memory(client_id)
    return {
        "client_id": client_id,
        "message": "Memory cleared successfully",
        "timestamp": datetime.now().isoformat()
    }

# --------------------------------------------------------
# Run Server
# --------------------------------------------------------
if __name__ == "__main__":
    logger.info("🚀 Starting Sales Experience Chatbot Server...")
    logger.info("💡 Using Sentence Transformers (all-MiniLM-L6-v2) for embeddings")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
