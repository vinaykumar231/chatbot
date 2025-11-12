# 🎯 BookAwestruck - AI Experience Recommendation Chatbot

An intelligent chatbot that helps users discover and book personalized experiences using AI-powered recommendations, vector search, and conversation memory.

---

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [How It Works](#how-it-works)
- [API Documentation](#api-documentation)
- [File Descriptions](#file-descriptions)

---

## ✨ Features

- **AI-Powered Recommendations**: Uses Google Gemini AI to understand user preferences
- **Semantic Search**: ChromaDB vector database with sentence transformers for intelligent matching
- **Conversation Memory**: Persistent memory across sessions for personalized interactions
- **Real-time Chat**: WebSocket-based communication for instant responses
- **Intent Detection**: Automatically detects user intent (greeting, experience request, casual chat)
- **User Profiling**: Learns and remembers user interests, budget, and location preferences
- **Database-Only Responses**: Only recommends verified experiences from the database

---

## 📁 Project Structure

```
ADENGAGE_CHABOT/
│
├── chroma_db/                          # Vector database storage (auto-created)
├── conversation_memory/                # User conversation history (auto-created)
├── __pycache__/                        # Python cache files
├── .venv/                              # Virtual environment
│
├── chatbot.py                          # Main AI chatbot logic
├── conversation_memory_manager.py      # Memory persistence handler
├── data_processor.py                   # Data loading & vector DB setup
├── main.py                             # FastAPI server & WebSocket endpoint
├── websocket_manager.py                # WebSocket connection manager
├── prompt.py                           # AI prompts and conversation templates
│
├── experiences_dataset_large.csv       # Experience data (required)
├── chatbot_frontend.html               # Web UI for the chatbot
│
├── .env                                # Environment variables (create this)
├── .gitignore                          # Git ignore file
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.9+, FastAPI, Uvicorn
- **AI Model**: Google Gemini 2.0 Flash
- **Vector Database**: ChromaDB with Sentence Transformers
- **Embeddings**: all-MiniLM-L6-v2 (local, no API key needed)
- **Frontend**: HTML, JavaScript, WebSocket
- **Memory**: Pickle-based persistent storage

---

## 📦 Prerequisites

- Python 3.9 or higher
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
- 2GB+ free disk space (for embeddings model)

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/vinaykumar231/RAG_chatbot.git
cd adengage_chatbot
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-dotenv==1.0.0
google-generativeai==0.3.1
chromadb==0.4.18
sentence-transformers==2.2.2
pandas==2.1.3
```

### Step 4: Download Dataset

Ensure `experiences_dataset_large.csv` is in the root directory with these columns:
- `id` - Unique experience ID
- `title` - Experience name
- `description` - Detailed description
- `category` - Experience category
- `location` - City/region
- `budget` - Price in INR

---

## ⚙️ Configuration

### Create `.env` File

Create a `.env` file in the root directory:

```bash
# Copy from template
cp .env.example .env
```

**`.env` content:**
```env
# Google Gemini API Key (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
CHROMA_PERSIST_DIR=./chroma_db
MEMORY_STORAGE_DIR=./conversation_memory

# Data Configuration
CSV_DATA_PATH=./experiences_dataset_large.csv

# Model Configuration
GEMINI_MODEL=gemini-2.0-flash-exp

```

**Get your Gemini API Key:**
1. Visit https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy and paste into `.env`

---

## 🎮 Running the Application

### Step 1: Start the Backend Server

```bash
python main.py
```

You should see:
```
INFO:     Starting Sales Experience Chatbot Server...
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Initializing ChromaDB...
INFO:     Loading Sentence Transformer model: all-MiniLM-L6-v2
INFO:     Around 100 experiences in ChromaDB
```

### Step 2: Open the Frontend

Open `chatbot_frontend.html` in your browser, or visit:
```
file:///path/to/adengage-chabot/chatbot_frontend.html
```

### Step 3: Start Chatting!

The chatbot will automatically connect. Try:
- "Hi, I'm looking for adventure activities"
- "Show me romantic getaways in Andheri"
- "Budget-friendly experiences in Mumbai"

---

## 🔍 How It Works

### 1. **Data Initialization** (`data_processor.py`)
```
CSV → Pandas DataFrame → Text Embeddings → ChromaDB
```
- Loads `experiences_dataset_large.csv`
- Generates semantic embeddings using Sentence Transformers
- Stores in ChromaDB for fast similarity search

### 2. **User Connection** (`websocket_manager.py`)
```
User → WebSocket → ConnectionManager → AI Instance
```
- Each user gets unique client ID
- AI instance created with personal conversation memory
- WebSocket maintains real-time connection

### 3. **Message Processing** (`chatbot.py`)
```
User Message → Intent Detection → AI Response Generation
```

**Intent Flow:**
```python
User: "Show me adventures in Goa"
  ↓
Intent: "experience_request"
  ↓
Vector Search: ChromaDB finds matching experiences
  ↓
AI Generation: Gemini creates personalized response
  ↓
Response: "I found 3 great adventures in Goa..."
```

### 4. **Memory Management** (`conversation_memory_manager.py`)
```
Conversation → Pickle File → Load on Reconnect
```
- Stores conversation history per user
- Remembers preferences (interests, budget, locations)
- Tracks previously discussed experiences

### 5. **Response Verification**
```
AI Response → Database Verification → Send to User
```
- AI can ONLY recommend experiences in database
- All details verified against source data
- Professional highlights generated from descriptions

---

## 📡 API Documentation

### WebSocket Endpoint

**URL:** `ws://localhost:8000/ws/chat/{client_id}`

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/user_123');
```

**Send Message:**
```javascript
ws.send(JSON.stringify({
    type: "chat",
    message: "Show me adventure activities"
}));
```

**Receive Response:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

### Message Types

#### 1. User Message (Send)
```json
{
    "type": "chat",
    "message": "Looking for romantic getaways"
}
```

#### 2. AI Response (Receive)
```json
{
    "type": "response",
    "message": "I found 3 romantic experiences...",
    "experiences": {
        "conversational_intro": "...",
        "experiences": [...],
        "conversational_closing": "..."
    },
    "timestamp": "2025-11-13T10:30:00"
}
```

#### 3. Clear Memory (Send)
```json
{
    "type": "clear_memory"
}
```

#### 4. Get Stats (Send)
```json
{
    "type": "get_stats"
}
```

---

## 📄 File Descriptions

### Core Files

| File | Purpose |
|------|---------|
| `chatbot.py` | Main AI logic, intent detection, response generation |
| `data_processor.py` | CSV loading, ChromaDB setup, vector search |
| `conversation_memory_manager.py` | Persistent memory storage and retrieval |
| `main.py` | FastAPI server, WebSocket endpoint |
| `websocket_manager.py` | Connection management, AI instance handling |
| `prompt.py` | AI prompts, templates, intent keywords |
| `chatbot_frontend.html` | User interface |

### Data Files

| File | Purpose |
|------|---------|
| `experiences_dataset_large.csv` | Experience database |
| `chroma_db/` | Vector database storage |
| `conversation_memory/` | User conversation histories |

### Configuration

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, paths) |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Git exclusions |

---

## 🎯 Key Features Explained

### 1. **Intent Detection**
Automatically classifies user messages:
- **Greeting**: "Hi", "Hello"
- **Experience Request**: "Show me", "Looking for"
- **Casual Chat**: General conversation
- **Exit**: "Bye", "Thanks, that's all"

### 2. **Semantic Search**
Uses vector embeddings to find experiences:
```python
Query: "romantic beach getaway"
  ↓
Embedding: [0.23, -0.15, 0.89, ...]
  ↓
ChromaDB: Finds similar experiences
  ↓
Results: Beach Resort, Couples Spa, Sunset Cruise
```

### 3. **User Profiling**
Learns from conversation:
```python
User: "Looking for adventure activities under ₹5000 in Goa"
  ↓
Extracted:
  - interests: ["adventure"]
  - budget: "₹5000"
  - locations: ["goa"]
```

### 4. **Database Verification**
Ensures accuracy:
```python
AI Response → Verify against database
  ↓
Match ID/Title/Budget → ✅ Send
  ↓
No Match → ❌ Use fallback
```

---

## 🐛 Troubleshooting

### Issue: "GEMINI_API_KEY not found"
**Solution:** Create `.env` file with valid API key

### Issue: ChromaDB initialization fails
**Solution:** Delete `chroma_db/` folder and restart

### Issue: WebSocket connection fails
**Solution:** Check if port 8000 is available:
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

### Issue: No experiences found
**Solution:** Verify `experiences_dataset_large.csv` exists and has data

---

## 📝 Example Conversation Flow

```
User: Hi there!
Bot: Hi there! I'm here to help you discover amazing experiences. 
     What kind of adventure are you thinking about?

User: Show me romantic getaways in Goa under ₹10000
Bot: Based on your interest in romantic experiences in Goa, I found: 
     Beach Resort Stay, Couple's Spa Package, Sunset Dinner Cruise.
     
     [Displays 3 detailed experience cards]
     
     Which one interests you most?

User: Tell me more about the beach resort
Bot: [Provides detailed information about Beach Resort Stay]

User: Thanks, I'll think about it
Bot: You're welcome! Take your time. I'm here whenever you're ready!
```

---

## 🔐 Security Notes

- Never commit `.env` file to Git
- Keep API keys confidential
- Use environment variables for sensitive data
- Validate all user inputs

---

## 📞 Support

For issues or questions:
- Check logs in terminal
- Review `README.md`
- Inspect browser console (F12)

---
