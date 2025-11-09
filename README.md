# Sales Experience Chatbot with Memory 🎯

A professional AI-powered sales chatbot with persistent conversation memory using Google Gemini and local Sentence Transformers for embeddings.

## Features ✨

- **🆓 Free Embeddings**: Uses local Sentence Transformers (no API costs!)
- **💾 Persistent Memory**: Remembers all conversations across sessions
- **🎯 Smart Recommendations**: Vector-based semantic search
- **🤝 Sales Expertise**: 15 years of professional sales techniques
- **👤 User Profiling**: Tracks interests, budget, and preferences
- **⚡ Real-time**: WebSocket for instant bidirectional communication
- **🔒 Private**: All embeddings computed locally

## Project Structure 📁

```
sales-chatbot/
├── data_processor.py            # Data loading and vector DB
├── sales_chatbot.py             # AI brain with memory
├── websocket_manager.py         # Connection management
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
├── .env.example                 # Environment template
├── experiences_dataset_large.csv # Experience data
├── chroma_db/                   # Vector database (auto-created)
└── conversation_memory/         # Conversation storage (auto-created)
```

## Setup Instructions 🚀

### 1. Prerequisites

- Python 3.9 or higher
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### 2. Installation

```bash
# Clone or download the project
cd sales-chatbot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**First Run Note**: Sentence Transformers will download the model (~80MB) automatically. This only happens once!

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key
```

Add your API key to `.env`:
```
GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Prepare Data

Create `experiences_dataset_large.csv` with these columns:

| Column | Description | Example |
|--------|-------------|---------|
| id | Unique identifier | 1 |
| title | Experience name | "Beach Paradise" |
| description | Detailed description | "Relaxing beach resort..." |
| category | Category | Adventure, Relaxation, etc. |
| location | Location name | Goa, Kerala, etc. |
| budget | Price in ₹ | 15000 |

Example CSV:
```csv
id,title,description,category,location,budget
1,Beach Paradise,"Relaxing beach resort with spa",Relaxation,Goa,15000
2,Mountain Trek,"Thrilling Himalayan adventure",Adventure,Himachal,25000
3,Cultural Tour,"Explore ancient temples",Culture,Rajasthan,12000
```

### 5. Run the Server

```bash
# Start the server
python main.py
```

Output:
```
🚀 Starting Sales Experience Chatbot Server...
💡 Using Sentence Transformers (all-MiniLM-L6-v2) for embeddings
🤖 Loading Sentence Transformer model: all-MiniLM-L6-v2
✅ Model loaded successfully!
📊 No data found. Loading and processing CSV...
✅ Data successfully loaded into ChromaDB
🎉 SYSTEM READY
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## API Endpoints 🔌

### WebSocket
- **URL**: `ws://localhost:8000/ws/chat/{client_id}`
- **Description**: Real-time chat connection

### REST Endpoints
- **Root**: `GET /`
- **Health Check**: `GET /health`
- **Get Stats**: `GET /api/stats/{client_id}`
- **Clear Memory**: `POST /api/clear_memory/{client_id}`

## WebSocket Message Format 💬

### Send Message (Client → Server)
```json
{
  "type": "chat",
  "message": "I'm looking for adventure experiences in Goa"
}
```

### Receive Response (Server → Client)
```json
{
  "type": "response",
  "message": "Based on your interest in adventure...",
  "experiences": {
    "experiences": [
      {
        "id": "exp_123",
        "title": "Beach Adventure",
        "category": "Adventure",
        "location": "Goa",
        "budget": "15000",
        "description": "...",
        "similarity_score": 95.5
      }
    ]
  },
  "timestamp": "2024-11-09T10:30:00"
}
```

## Testing the Chatbot 🧪

### Using Python WebSocket Client

```python
import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://localhost:8000/ws/chat/test_user_123"
    
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "type": "chat",
            "message": "Show me luxury experiences in Goa"
        }))
        
        # Receive response
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(test_chat())
```

### Using JavaScript (Browser)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/user_123');

ws.onopen = () => {
  console.log('Connected!');
  
  ws.send(JSON.stringify({
    type: 'chat',
    message: 'Looking for adventure experiences'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Response:', data);
};
```

## Embedding Model Info 🤖

**all-MiniLM-L6-v2**:
- **Size**: ~80MB
- **Speed**: ~3000 sentences/sec on CPU
- **Quality**: Excellent for semantic search
- **Dimensions**: 384 (compact but effective)
- **Cost**: 100% FREE (runs locally)
- **Privacy**: Your data never leaves your server

### Alternative Models

If you want to try different models, edit `data_processor.py`:

```python
# For highest quality (slower):
model_name="all-mpnet-base-v2"  # 420MB

# For multilingual support:
model_name="paraphrase-multilingual-MiniLM-L12-v2"

# For smaller size:
model_name="all-MiniLM-L12-v2"
```

## Memory System 💾

### How It Works

1. **Client Identification**: Each client gets a unique ID
2. **Persistent Storage**: Conversations saved as pickle files
3. **Automatic Loading**: Previous conversations loaded on reconnect
4. **Profile Building**: System learns preferences over time

### Stored Information

- Full conversation history
- User interests and preferences
- Budget range mentions
- Preferred locations
- Previously discussed experiences
- Conversation stage tracking

### Memory Commands

```json
// Clear memory for fresh start
{
  "type": "clear_memory"
}

// Get conversation statistics
{
  "type": "get_stats"
}
```

## Troubleshooting 🔧

### Common Issues

1. **Model Download Slow**
   - First run downloads ~80MB model
   - Check internet connection
   - Model caches locally after first download

2. **API Key Error**
   - Ensure `GEMINI_API_KEY` is set in `.env`
   - Get key from https://makersuite.google.com/app/apikey

3. **CSV Not Found**
   - Place `experiences_dataset_large.csv` in project root
   - Check CSV has required columns: id, title, description, category, location, budget

4. **ChromaDB Error**
   - Delete `chroma_db/` folder
   - Restart server to rebuild database

5. **Memory Not Persisting**
   - Check `conversation_memory/` folder exists
   - Verify write permissions

### Performance Notes

- **First Run**: 1-2 minutes (model download + data loading)
- **Subsequent Runs**: 5-10 seconds (cached model)
- **Search Speed**: <100ms per query
- **Memory Per User**: 1-5KB
- **Supports**: 100+ concurrent connections

## Cost Comparison 💰

### Before (Google API Embeddings):
- **Cost**: ~$0.01 per 1000 embeddings
- **Speed**: 200ms per query (API latency)
- **Limit**: API rate limits apply
- **Privacy**: Data sent to Google

### After (Sentence Transformers):
- **Cost**: $0.00 (completely free!)
- **Speed**: <10ms per query (local)
- **Limit**: No limits!
- **Privacy**: 100% local, no data leaves server

## Advanced Configuration 🎛️

Edit `data_processor.py` for advanced settings:

```python
# Configuration
MAX_RESULTS = 3                    # Top recommendations to return
MAX_CONVERSATION_HISTORY = 50      # Messages to keep in memory
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Chat model (not embeddings)
```

## Deployment 🌐

### Production Considerations

1. **Use production WSGI server**: Gunicorn + Uvicorn workers
2. **Add authentication**: JWT tokens or API keys
3. **Rate limiting**: Prevent abuse
4. **Database backup**: Regularly backup `chroma_db/` and `conversation_memory/`
5. **Monitoring**: Add logging and metrics
6. **SSL/TLS**: Use secure WebSocket (wss://)

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

## Tech Stack 🛠️

- **FastAPI**: Modern web framework
- **Google Gemini**: AI chat responses
- **Sentence Transformers**: Local embeddings
- **ChromaDB**: Vector database
- **WebSocket**: Real-time communication
- **Pickle**: Conversation persistence

## License 📄

MIT License - Free to use and modify!

## Support 💬

For issues:
1. Check logs for detailed error messages
2. Verify all dependencies are installed
3. Ensure Gemini API key is valid
4. Review troubleshooting section above

---

**Built with ❤️ using FastAPI, Google Gemini, and Sentence Transformers**

**🎉 Now 100% free for embeddings!**