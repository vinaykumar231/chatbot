# sales_chatbot.py
"""
Professional Sales Experience Chatbot with Smart Intent Detection
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
import json

import google.generativeai as genai
from conversation_memory_manager import ConversationMemory
from data_processor import (
    SalesVectorDB, 
    GEMINI_MODEL, 
    MEMORY_STORAGE_DIR, 
    MAX_CONVERSATION_HISTORY,
    MAX_RESULTS
)
from prompt import SALES_PROMPTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== SMART EXPERIENCE PLANNER AI ====================

class ProfessionalSalesAI:
    """AI Assistant with Intent Detection and Smart Response for Experiences"""
    
    def __init__(self, api_key: str, vector_db: SalesVectorDB, memory_manager: ConversationMemory, client_id: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2000,
            }
        )
        
        self.vector_db = vector_db
        self.memory_manager = memory_manager
        self.client_id = client_id
        
        # Load existing conversation memory
        self.conversation_data = self.memory_manager.load_conversation(client_id)
        
        logger.info(f"🎯 Experience AI Initialized for {client_id}")
        logger.info(f"📊 Loaded: {self.conversation_data['total_messages']} previous messages, {len(self.conversation_data['user_profile']['interests'])} known interests")
    
    def check_exit_intent(self, text: str) -> bool:
        """Check if user wants to exit"""
        exit_phrases = ['stop', 'exit', 'quit', 'goodbye', 'bye', 'that\'s all',
                       'thank you bye', 'end conversation', 'thanks bye']
        text_lower = text.lower().strip()
        
        if text_lower in exit_phrases:
            return True
        
        for phrase in exit_phrases:
            if phrase in text_lower and len(text_lower.split()) <= 4:
                return True
        
        return False
    
    async def detect_intent_and_respond(self, user_input: str) -> Tuple[str, Optional[Dict], bool]:
        """
        Detect user intent and generate appropriate response
        Returns: (response_text, experience_data, is_farewell)
        """
        try:
            print("\n" + "="*70)
            print(f" PROCESSING USER INPUT: '{user_input}'")
            print("="*70)
            
            # Add to conversation
            self.conversation_data['history'].append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Check exit intent
            if self.check_exit_intent(user_input):
                print(" EXIT INTENT DETECTED")
                farewell = "Thank you for exploring experiences with me! Hope you find the perfect adventure. Have a wonderful day! "
                self._save_to_memory(user_input, farewell)
                return farewell, None, True
            
            # Extract user preferences from current input
            self._extract_user_preferences(user_input)
            
            # Step 1: Detect Intent
            print("\n STEP 1: Detecting Intent...")
            intent = await self._detect_intent(user_input)
            print(f" INTENT DETECTED: {intent}")
            
            # Step 2: Generate Response based on Intent
            if intent == "experience_request":
                print("\n STEP 2: Generating EXPERIENCE RESPONSE...")
                response_text, experience_data = await self._generate_experience_response(user_input)
                
                print("\n" + "="*70)
                print(" EXPERIENCE GENERATION RESULTS:")
                print("="*70)
                print(f" Response Text: {response_text[:100]}...")
                if experience_data:
                    print(f" Experience Data Generated: YES")
                    print(f"   - Number of experiences: {len(experience_data.get('experiences', []))}")
                    for i, exp in enumerate(experience_data.get('experiences', []), 1):
                        print(f"   - Experience {i}: {exp.get('title', 'N/A')}")
                else:
                    print(" Experience Data Generated: NO (None returned)")
                print("="*70 + "\n")
                
                return response_text, experience_data, False
            else:
                print("\n STEP 2: Generating CASUAL RESPONSE...")
                response_text = await self._generate_casual_response(user_input)
                print(f" Casual Response: {response_text[:100]}...")
                return response_text, None, False
            
        except Exception as e:
            logger.error(f" Error in intent detection: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I had trouble processing that. Could you say that again?", None, False
    
    async def _detect_intent(self, user_input: str) -> str:
        """Detect if user wants experience recommendations or casual chat"""
        
        intent_prompt = f"""Analyze this user message and determine their intent.

USER MESSAGE: "{user_input}"

CONVERSATION HISTORY:
{self._build_context()}

USER PREFERENCES:
{self._build_user_profile_summary()}

INTENT CATEGORIES:
1. "experience_request" - User is asking for:
   - Experience suggestions/recommendations/ideas
   - Activities or things to do
   - Travel destinations or places to visit
   - Adventure activities, tours, getaways
   - Specific experiences or activities
   - Words like: suggest, recommend, looking for, want to, interested in, things to do, activities, experiences, adventures, tours, trips

2. "casual_chat" - User is:
   - Greeting (hi, hello, hey)
   - Having general conversation
   - Asking about the assistant's capabilities
   - Expressing gratitude (thank you)
   - Asking for introduction/about me
   - Any non-experience-related queries

RESPOND WITH ONLY ONE WORD: Either "experience_request" or "casual_chat"

YOUR RESPONSE:"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                intent_prompt
            )
            
            intent = response.text.strip().lower()
            print(f"   Raw Intent Response: '{intent}'")
            
            # Validate response
            if "experience_request" in intent or "experience" in intent:
                return "experience_request"
            else:
                return "casual_chat"
                
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            # Default to casual if unsure
            return "casual_chat"
    
    async def _generate_casual_response(self, user_input: str) -> str:
        """Generate natural conversational response"""
        
        casual_prompt = f"""You are a friendly experience planning assistant having a natural conversation.

CONVERSATION HISTORY:
{self._build_context()}

USER PREFERENCES:
{self._build_user_profile_summary()}

USER MESSAGE: "{user_input}"

INSTRUCTIONS:
- Respond naturally and warmly (50-100 words)
- If user greets, greet back and ask how you can help with experiences
- If user thanks you, acknowledge graciously
- If user asks about your capabilities, explain you can help with experience suggestions, activities, and travel planning
- If user asks for introduction, briefly introduce yourself as an experience consultant
- Keep it conversational and friendly
- DO NOT provide experience recommendations unless explicitly asked
- Consider user's interests: {', '.join(self.conversation_data['user_profile']['interests']) if self.conversation_data['user_profile']['interests'] else 'No specific interests yet'}

YOUR RESPONSE (natural text, no JSON):"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                casual_prompt
            )
            
            response_text = response.text.strip()
            
            self._save_to_memory(user_input, response_text)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Casual response error: {e}")
            return "Hello! I'm here to help you discover amazing experiences. What would you like to explore today?"
    
    async def _generate_experience_response(self, user_input: str) -> Tuple[str, Optional[Dict]]:
        """Generate experience recommendations with structured data"""
        
        print("    Building experience generation prompt...")
        
        # Search for relevant experiences
        search_results = self.vector_db.search_experiences(user_input, n_results=8)
        
        if not search_results:
            # No experiences found - general engagement
            engagement_prompt = SALES_PROMPTS["engagement_with_memory"].format(
                conversation_context=self._build_context(),
                user_profile=self._build_user_profile_summary(),
                previous_experiences=self._build_previous_experiences_summary(),
                user_input=user_input
            )
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                engagement_prompt
            )
            
            response_text = response.text.strip()
            self._save_to_memory(user_input, response_text)
            return response_text, None
            
        else:
            # Found experiences - generate recommendations
            unique_experiences = {}
            for result in search_results:
                exp_id = result['metadata']['id']
                if exp_id not in unique_experiences or result['similarity_score'] > unique_experiences[exp_id]['similarity_score']:
                    unique_experiences[exp_id] = result
            
            top_experiences = sorted(
                unique_experiences.values(), 
                key=lambda x: x['similarity_score'], 
                reverse=True
            )[:MAX_RESULTS]
            
            # Format experiences for presentation
            experiences_context = "\n\n".join([
                f"Experience {i+1}:\n"
                f"Title: {exp['metadata']['title']}\n"
                f"Category: {exp['metadata']['category']}\n"
                f"Location: {exp['metadata']['location']}\n"
                f"Budget: ₹{exp['metadata']['budget']}\n"
                f"Description: {exp['metadata']['description']}\n"
                f"Match Score: {exp['similarity_score']}%"
                for i, exp in enumerate(top_experiences)
            ])
            
            experience_prompt = f"""You are a friendly experience planning assistant.

CONVERSATION HISTORY:
{self._build_context()}

USER PREFERENCES:
{self._build_user_profile_summary()}

PREVIOUSLY DISCUSSED:
{self._build_previous_experiences_summary()}

USER REQUEST: "{user_input}"

AVAILABLE OPTIONS:
{experiences_context}

INSTRUCTIONS:
1. Provide 1-3 experience suggestions based on the request AND user preferences
2. Include engaging descriptions for each experience
3. Be warm and conversational
4. Remember previous suggestions and avoid repetition
5. ALWAYS return valid JSON with the exact format below
6. Consider user interests: {', '.join(self.conversation_data['user_profile']['interests']) if self.conversation_data['user_profile']['interests'] else 'General experiences'}
7. Consider budget preference: {self.conversation_data['user_profile']['budget_range'] or 'Flexible'}
8. Consider location preference: {', '.join(self.conversation_data['user_profile']['preferred_locations']) or 'Any location'}

OUTPUT FORMAT (MUST BE VALID JSON):
{{
    "conversational_intro": "Brief friendly intro mentioning personalization (1-2 sentences)",
    "experiences": [
        {{
            "id": "experience_id",
            "title": "Exact experience name",
            "category": "Experience category",
            "location": "Location",
            "budget": "₹budget_amount",
            "description": "2-3 sentences describing the experience and its appeal",
            "duration": "2-3 hours",
            "best_for": "Couples/Friends/Family/Solo",
            "highlights": ["Highlight 1", "Highlight 2", "Highlight 3"],
            "inclusions": ["What's included 1", "What's included 2"],
            "similarity_score": 85,
            "why_perfect": "Brief note on why this suits user preferences",
            "urgency_factor": "Limited availability this season"
        }}
    ],
    "conversational_closing": "Brief friendly closing (1 sentence)"
}}

IMPORTANT: Return ONLY the JSON object, no other text before or after!

YOUR RESPONSE:"""

        try:
            print("    Calling Gemini API for experience generation...")
            response = await asyncio.to_thread(
                self.model.generate_content,
                experience_prompt
            )
            
            response_text = response.text.strip()
            print(f"    Raw API Response Length: {len(response_text)} characters")
            print(f"    First 200 chars: {response_text[:200]}")
            
            # Try to extract JSON with multiple methods
            experience_data = None
            
            # Method 1: Look for JSON between ```json and ```
            json_code_block = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_code_block:
                print("    Found JSON in code block")
                try:
                    experience_data = json.loads(json_code_block.group(1))
                except Exception as e:
                    print(f"    Failed to parse JSON from code block: {e}")
            
            # Method 2: Look for any JSON object
            if not experience_data:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    print("    Found JSON object in response")
                    try:
                        experience_data = json.loads(json_match.group())
                    except Exception as e:
                        print(f"    Failed to parse JSON: {e}")
                        print(f"    Problematic JSON: {json_match.group()[:500]}")
            
            # Method 3: Try parsing entire response as JSON
            if not experience_data:
                print("    Trying to parse entire response as JSON...")
                try:
                    experience_data = json.loads(response_text)
                    print("    Successfully parsed entire response as JSON")
                except Exception as e:
                    print(f"    Failed to parse entire response: {e}")
            
            if experience_data:
                print("    EXPERIENCE DATA SUCCESSFULLY PARSED")
                print(f"    Experiences in data: {len(experience_data.get('experiences', []))}")
                
                # Build conversational response
                intro = experience_data.get("conversational_intro", "Here are some great personalized options for you!")
                closing = experience_data.get("conversational_closing", "Let me know if you'd like more details!")
                
                # Format experience names
                exp_names = [exp.get("title", "Unknown Experience") for exp in experience_data.get('experiences', [])]
                exps_text = ", ".join(exp_names)
                
                conversational_text = f"{intro} I suggest: {exps_text}. {closing}"
                
                self._save_to_memory(user_input, conversational_text, experience_data)
                
                print(f"    Returning conversational text and experience data")
                return conversational_text, experience_data
            else:
                print("    FAILED TO EXTRACT EXPERIENCE DATA FROM RESPONSE")
                # Fallback to direct experience formatting
                conversational_text = "I found some great experiences for you! "
                exp_names = [exp['metadata']['title'] for exp in top_experiences[:3]]
                conversational_text += ", ".join(exp_names) + ". Which one interests you most?"
                
                # Create basic experience data
                experience_data = {
                    "conversational_intro": conversational_text,
                    "experiences": [
                        {
                            "id": exp['metadata']['id'],
                            "title": exp['metadata']['title'],
                            "category": exp['metadata']['category'],
                            "location": exp['metadata']['location'],
                            "budget": f"₹{exp['metadata']['budget']}",
                            "description": exp['metadata']['description'],
                            "similarity_score": exp['similarity_score'],
                            "why_perfect": f"Matches your interest in {user_input}"
                        }
                        for exp in top_experiences[:3]
                    ]
                }
                
                self._save_to_memory(user_input, conversational_text, experience_data)
                return conversational_text, experience_data
            
        except Exception as e:
            logger.error(f" Experience response error: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "I'd love to suggest some amazing experiences! Could you tell me what type of activities you're interested in?"
            return error_msg, None
    
    def _extract_user_preferences(self, user_input: str):
        """Extract and store user preferences from input"""
        input_lower = user_input.lower()
        
        # Extract interests
        interest_keywords = {
            'adventure': ['adventure', 'thrill', 'exciting', 'action', 'trek', 'climb', 'raft', 'paragliding'],
            'relaxation': ['relax', 'peaceful', 'calm', 'quiet', 'serene', 'spa', 'yoga', 'meditation'],
            'culture': ['culture', 'historical', 'traditional', 'heritage', 'temple', 'monument'],
            'nature': ['nature', 'outdoor', 'forest', 'mountain', 'beach', 'wildlife', 'camping'],
            'romantic': ['romantic', 'honeymoon', 'couple', 'anniversary', 'date', 'couples'],
            'luxury': ['luxury', 'premium', 'exclusive', 'vip', '5 star', 'resort']
        }
        
        for interest, keywords in interest_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                if interest not in self.conversation_data['user_profile']['interests']:
                    self.conversation_data['user_profile']['interests'].append(interest)
        
        # Extract budget mentions
        budget_patterns = [r'budget.*?(\d+)', r'(\d+).*?budget', r'₹\s*(\d+)', r'rs\.?\s*(\d+)']
        for pattern in budget_patterns:
            match = re.search(pattern, input_lower)
            if match:
                self.conversation_data['user_profile']['budget_range'] = f"₹{match.group(1)}"
                break
        
        # Extract location mentions
        location_keywords = ['goa', 'kerala', 'himachal', 'rajasthan', 'mumbai', 'delhi', 'bangalore']
        for location in location_keywords:
            if location in input_lower:
                if location not in self.conversation_data['user_profile']['preferred_locations']:
                    self.conversation_data['user_profile']['preferred_locations'].append(location)
    
    def _build_context(self) -> str:
        """Build conversation context"""
        if not self.conversation_data['history']:
            return "This is the start of the conversation."
        
        context_lines = ["Recent conversation:"]
        # Use last 5 exchanges
        recent = self.conversation_data['history'][-10:]
        
        for i, msg in enumerate(recent, 1):
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content'][:150]  # Truncate long messages
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)
    
    def _build_user_profile_summary(self) -> str:
        """Build summary of known user preferences"""
        profile = self.conversation_data['user_profile']
        
        summary = "Known Client Preferences:\n"
        if profile['interests']:
            summary += f"- Interests: {', '.join(profile['interests'])}\n"
        if profile['budget_range']:
            summary += f"- Budget: {profile['budget_range']}\n"
        if profile['preferred_locations']:
            summary += f"- Preferred Locations: {', '.join(profile['preferred_locations'])}\n"
        
        return summary if summary != "Known Client Preferences:\n" else "No specific preferences recorded yet."
    
    def _build_previous_experiences_summary(self) -> str:
        """Build summary of previously discussed experiences"""
        previous_exps = self.conversation_data['previously_discussed_experiences'][-5:]
        
        if not previous_exps:
            return "No experiences discussed previously."
        
        summary = "Previously Discussed Experiences:\n"
        for exp in previous_exps:
            summary += f"- {exp.get('title', 'Unknown')} (Category: {exp.get('category', 'Unknown')})\n"
        
        return summary
    
    def _save_to_memory(self, user_input: str, assistant_response: str, experience_data: Optional[Dict] = None):
        """Save current interaction to memory"""
        # Add to conversation history
        self.conversation_data['history'].append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        self.conversation_data['history'].append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.now().isoformat(),
            "experience_data": experience_data
        })
        
        # Limit history size
        if len(self.conversation_data['history']) > MAX_CONVERSATION_HISTORY:
            self.conversation_data['history'] = self.conversation_data['history'][-MAX_CONVERSATION_HISTORY:]
        
        # Update metadata
        self.conversation_data['total_messages'] = len(self.conversation_data['history'])
        self.conversation_data['last_interaction'] = datetime.now().isoformat()
        
        # Add discussed experiences
        if experience_data and 'experiences' in experience_data:
            for exp in experience_data['experiences']:
                if exp not in self.conversation_data['previously_discussed_experiences']:
                    self.conversation_data['previously_discussed_experiences'].append(exp)
        
        # Save to persistent storage
        self.memory_manager.save_conversation(self.client_id, self.conversation_data)
    
    def clear_conversation_memory(self):
        """Clear conversation memory for this client"""
        self.memory_manager.delete_conversation(self.client_id)
        self.conversation_data = self.memory_manager.load_conversation(self.client_id)
        logger.info(f"🗑️ Cleared conversation memory for {self.client_id}")
    
    def get_conversation_stats(self) -> Dict:
        """Get conversation statistics"""
        return self.memory_manager.get_conversation_stats(self.client_id)
    
    def get_full_conversation_history(self) -> List[Dict]:
        """Get full conversation history"""
        return self.conversation_data['history']