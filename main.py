import logging
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from websocket_manager import manager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------
# WebSocket Endpoint
# --------------------------------------------------------

@app.websocket("/ws/chat/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    
    await manager.connect(websocket, client_id)
    
    try:
        await manager.send_message(client_id, {
            "type": "system",
            "message": "Connected to Experience Consultant! ",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received from {client_id}: {data}")
        
            message_type = data.get("type", "chat")
            if message_type == "user_message":
                message_type = "chat"
            
            user_message = data.get("message", "")
            
            if message_type == "chat" and user_message:
                ai_brain = manager.get_ai_brain(client_id)
                
                if not ai_brain:
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": "AI brain not initialized. Please reconnect."
                    })
                    continue
                
                await manager.send_message(client_id, {
                    "type": "typing",
                    "timestamp": datetime.now().isoformat()
                })
                
                try:
                    logger.info(f"Generating response for: {user_message}")
                    
                    response_text, experience_data, is_farewell = await ai_brain.detect_intent_and_respond(user_message)
                    
                    logger.info(f" Response generated: {response_text[:100]}...")
                    
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
                    logger.error(f"Error generating response for {client_id}: {e}", exc_info=True)
                    await manager.send_message(client_id, {
                        "type": "error",
                        "message": "Sorry, I encountered an error. Please try again."
                    })
            
            elif message_type == "clear_memory":
                manager.clear_client_memory(client_id)
                await manager.send_message(client_id, {
                    "type": "system",
                    "message": "Conversation memory cleared! Starting fresh. ",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif message_type == "get_stats":
                stats = manager.get_client_stats(client_id)
                await manager.send_message(client_id, {
                    "type": "stats",
                    "data": stats,
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                logger.warning(f" Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"🔌 Client {client_id} disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)


# --------------------------------------------------------
# Run Server
# --------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Sales Experience Chatbot Server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
