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

# ==================== PROFESSIONAL SALES AI - DATABASE ONLY ====================

class ProfessionalSalesAI:
    """AI Assistant - Strictly Database-Only Information, Temperature 0.3"""
    
    def __init__(self, api_key: str, vector_db: SalesVectorDB, memory_manager: ConversationMemory, client_id: str):
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                "temperature": 0.3,  
                "max_output_tokens": 2000,
                "top_p": 0.8,  
                "top_k": 20    
            }
        )
        
        self.vector_db = vector_db
        self.memory_manager = memory_manager
        self.client_id = client_id
        
        self.conversation_data = self.memory_manager.load_conversation(client_id)
            
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

        try:
            self.conversation_data['history'].append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            if self.check_exit_intent(user_input):
                farewell = "Thank you for exploring experiences with me! Hope you find the perfect adventure. Have a wonderful day!"
                self._save_to_memory(user_input, farewell)
                return farewell, None, True
            
            self._extract_user_preferences(user_input)
            
            intent = await self._detect_intent(user_input)
            
            if intent == "experience_request":
                logger.info("STEP 2: Generating DATABASE-VERIFIED EXPERIENCE RESPONSE...")
                response_text, experience_data = await self._generate_experience_response(user_input)
                
                if experience_data:
                    logger.info("Experience Data: VERIFIED FROM DATABASE")
                    for i, exp in enumerate(experience_data.get('experiences', []), 1):
                        logger.info(f"   - Experience {i}: {exp.get('title', 'N/A')}")
                else:
                    logger.info("Experience Data: NONE FOUND IN DATABASE")
                logger.info("="*70)
                
                return response_text, experience_data, False
            else:
                logger.info("STEP 2: Generating CASUAL RESPONSE...")
                response_text = await self._generate_casual_response(user_input)
                logger.info(f"Casual Response: {response_text[:100]}...")
                return response_text, None, False
            
        except Exception as e:
            logger.error(f"Error in intent detection: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I had trouble processing that. Could you say that again?", None, False
    
    async def _detect_intent(self, user_input: str) -> str:
        """Detect if user wants experience recommendations or casual chat"""
        
        intent_prompt = f"""Analyze this user message and determine their intent.

USER MESSAGE: "{user_input}"

CONVERSATION HISTORY:
{self._build_context()}

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
            logger.debug(f"Raw Intent Response: '{intent}'")
            
            if "experience_request" in intent or "experience" in intent:
                return "experience_request"
            else:
                return "casual_chat"
                
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return "casual_chat"
    
    async def _generate_casual_response(self, user_input: str) -> str:
        """Generate natural conversational response"""
        
        casual_prompt = f"""You are a professional experience planning assistant.

CONVERSATION HISTORY:
{self._build_context()}

USER MESSAGE: "{user_input}"

INSTRUCTIONS:
- Respond naturally and professionally (40-80 words)
- If user greets, greet back and mention you help with verified database experiences
- If user thanks you, acknowledge graciously
- If user asks about capabilities, explain you provide ONLY verified database recommendations
- Keep it conversational and professional
- DO NOT provide experience recommendations unless explicitly asked
- DO NOT make up or assume any information

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
            return "Hello! I'm here to help you discover verified experiences from our database. What would you like to explore today?"
    
    async def _generate_experience_response(self, user_input: str) -> Tuple[str, Optional[Dict]]:
        """Generate experience recommendations ONLY from verified database"""
        
        search_results = self.vector_db.search_experiences(user_input, n_results=10)
        
        if not search_results:
            no_results_response = f"""I searched our database but couldn't find experiences matching "{user_input}".

To help you better, could you tell me:
- What type of activity interests you? (adventure, relaxation, culture, nature)
- Your preferred location?
- Your approximate budget?

This will help me find verified experiences from our database."""
            
            self._save_to_memory(user_input, no_results_response)
            return no_results_response, None
            
        else:
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
            
            verified_experiences_text = "\n\n".join([
                f"VERIFIED EXPERIENCE {i+1} (Database ID: {exp['metadata']['id']}):\n"
                f"Title: {exp['metadata']['title']}\n"
                f"Category: {exp['metadata']['category']}\n"
                f"Location: {exp['metadata']['location']}\n"
                f"Budget: ₹{exp['metadata']['budget']}\n"
                f"Description: {exp['metadata']['description']}\n"
                f"Match Score: {exp['similarity_score']}%"
                for i, exp in enumerate(top_experiences)
            ])
            
            experience_prompt = f"""You are a professional experience consultant presenting verified database information.

CRITICAL RULES (Temperature 0.3 - Factual Mode):
1. Use ONLY the verified experiences provided below - NO INVENTION
2. Copy id, title, category, location, budget, description EXACTLY as provided
3. For "why_perfect": Craft compelling 1 sentence explanation based ONLY on:
   - Database category, location, and description
   - User's stated request and preferences
   - Make it professional and persuasive but 100% truthful
4. For "highlights": Generate exactly 3 benefit-focused highlights:
   - Analyze the database description carefully
   - Extract or intelligently derive 3 key benefits
   - Each must be ONE complete sentence
   - Make them attractive but truthful
   - If description is sparse, focus on category and location benefits
5. Be persuasive in presentation while staying completely factual

CONVERSATION CONTEXT:
{self._build_context()}

USER PREFERENCES:
{self._build_user_profile_summary()}

USER REQUEST: "{user_input}"

VERIFIED DATABASE EXPERIENCES (Use ONLY this information):
{verified_experiences_text}

YOUR TASK:
Present these verified experiences professionally and compellingly. Return ONLY valid JSON:

{{
    "conversational_intro": "Warm, personalized intro mentioning their preferences (1-2 sentences)",
    "experiences": [
        {{
            "id": "exact_database_id",
            "title": "exact_title_from_database",
            "category": "exact_category_from_database",
            "location": "exact_location_from_database",
            "budget": "₹exact_budget_from_database",
            "description": "exact_description_from_database",
            "similarity_score": exact_match_score,
            "why_perfect": "Brief note on why this suits user preferences",
            "highlights": ["Highlight 1", "Highlight 2", "Highlight 3"],
        }}
    ],
    "conversational_closing": "Engaging closing that invites action (1 sentence)"
}}


IMPORTANT:
- Include ALL {len(top_experiences)} verified experiences
- Each highlight must be exactly ONE sentence
- Make presentation compelling but stay 100% truthful to database
- Do NOT add fields like "duration", "best_for", "inclusions" unless in database
- Return ONLY the JSON object

YOUR RESPONSE:"""

            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    experience_prompt
                )
                
                response_text = response.text.strip()
                
                experience_data = self._extract_json_safely(response_text)
                
                if experience_data and 'experiences' in experience_data:
                    logger.info("Successfully extracted verified experience data")
                    
                    verified_data = self._verify_experience_data(experience_data, top_experiences)
                    
                    intro = verified_data.get("conversational_intro", "Here are verified experiences from our database:")
                    closing = verified_data.get("conversational_closing", "Which one interests you?")
                    
                    exp_names = [exp.get("title") for exp in verified_data.get('experiences', [])]
                    exps_text = ", ".join(exp_names)
                    
                    conversational_text = f"{intro} I found: {exps_text}. {closing}"
                    
                    self._save_to_memory(user_input, conversational_text, verified_data)
                    
                    return conversational_text, verified_data
                else:
                    logger.warning("JSON extraction failed, using fallback")
                    return self._create_fallback_response(user_input, top_experiences)
                
            except Exception as e:
                logger.error(f"Experience response error: {e}")
                import traceback
                traceback.print_exc()
                return self._create_fallback_response(user_input, top_experiences)
    
    def _verify_experience_data(self, ai_data: Dict, database_results: List[Dict]) -> Dict:
        """Verify AI response matches database and has professional enhancements"""
        
        db_lookup = {exp['metadata']['id']: exp['metadata'] for exp in database_results}
        
        verified_experiences = []
        
        for exp in ai_data.get('experiences', []):
            exp_id = exp.get('id')
            
            if exp_id in db_lookup:
                db_exp = db_lookup[exp_id]
                
                verified_exp = {
                    'id': db_exp['id'],
                    'title': db_exp['title'],
                    'category': db_exp['category'],
                    'location': db_exp['location'],
                    'budget': f"₹{db_exp['budget']}",
                    'description': db_exp['description'],
                    'similarity_score': next((r['similarity_score'] for r in database_results if r['metadata']['id'] == exp_id), 0),
                }
                
                why_perfect = exp.get('why_perfect', '').strip()
                if why_perfect and len(why_perfect) > 20 and len(why_perfect) < 300:
                    verified_exp['why_perfect'] = why_perfect
                    logger.debug(f"AI Why Perfect: {why_perfect[:60]}...")
                else:
                    verified_exp['why_perfect'] = self._generate_professional_why_perfect(db_exp, user_input=self.conversation_data['history'][-1]['content'] if self.conversation_data['history'] else "")
                    logger.warning("Using fallback why_perfect")
                
                highlights = exp.get('highlights', [])
                if highlights and isinstance(highlights, list) and len(highlights) >= 2:
                    clean_highlights = []
                    for h in highlights[:3]:
                        h_clean = h.strip()
                        first_sentence = h_clean.split('.')[0].strip()
                        if len(first_sentence) > 10:
                            if not first_sentence.endswith(('.', '!', '?')):
                                first_sentence += '.'
                            clean_highlights.append(first_sentence[:200])
                    
                    if len(clean_highlights) >= 2:
                        verified_exp['highlights'] = clean_highlights[:3]
                        logger.debug(f"AI Highlights: {len(verified_exp['highlights'])} single-sentence highlights")
                    else:
                        verified_exp['highlights'] = self._generate_professional_highlights(db_exp['description'], db_exp['category'])
                        logger.warning("Using fallback highlights")
                else:
                    verified_exp['highlights'] = self._generate_professional_highlights(db_exp['description'], db_exp['category'])
                    logger.warning("Using fallback highlights")
                
                verified_experiences.append(verified_exp)
                logger.info(f"Verified: {db_exp['title']}")
            else:
                logger.warning(f"Rejected: ID {exp_id} not in database")
        
        return {
            'conversational_intro': ai_data.get('conversational_intro', 'Here are personalized experiences for you:'),
            'experiences': verified_experiences,
            'conversational_closing': ai_data.get('conversational_closing', 'Which experience excites you most?')
        }
    
    def _generate_professional_why_perfect(self, experience: Dict, user_input: str = "") -> str:
        """Generate professional, compelling why_perfect from database fields"""
        
        category = experience.get('category', 'experience')
        location = experience.get('location', 'this location')
        description = experience.get('description', '').lower()
        user_input_lower = user_input.lower()
        
        if 'adventure' in category.lower() or 'thrill' in description:
            return f"Perfect for adventure enthusiasts! This {category.lower()} experience in {location} delivers excitement and unforgettable thrills."
        elif 'spa' in description or 'relax' in description or 'wellness' in category.lower():
            return f"Ideal for unwinding and rejuvenation! This {location} experience offers the peaceful escape with professional care."
        elif 'romantic' in description or 'couple' in description:
            return f"Perfect romantic getaway! This {category.lower()} experience in {location} creates intimate moments and lasting memories."
        elif 'cultural' in category.lower() or 'heritage' in description:
            return f"Immerse yourself in authentic culture! This {location} experience showcases rich heritage and traditions."
        elif location.lower() in user_input_lower:
            return f"Excellent choice for {location}! This {category.lower()} experience offers unique value perfectly matching your destination preference."
        else:
            return f"Great match for your interests! This {category.lower()} experience in {location} offers authentic value and memorable moments."
    
    def _generate_professional_highlights(self, description: str, category: str) -> List[str]:
        """Generate professional, benefit-focused highlights from description (3 single sentences)"""
        
        if not description or len(description.strip()) < 20:
            return [
                f"Authentic {category.lower()} experience curated by local experts.",
                "Professional service and guidance throughout your journey.",
                "Complete details available upon inquiry for personalized planning."
            ]
        
        highlights = []
        
        sentences = [s.strip() for s in description.split('.') if len(s.strip()) > 15]
        
        for sentence in sentences[:3]:
            clean_sentence = sentence.split('.')[0].strip()
            
            # Make it benefit-focused if too plain
            if len(clean_sentence) < 30:
                clean_sentence = f"{clean_sentence} for an unforgettable experience"
            
            # Ensure proper ending
            if not clean_sentence.endswith(('.', '!', '?')):
                clean_sentence += '.'
            
            highlights.append(clean_sentence[:200])
        
        # Ensure exactly 3 highlights
        if len(highlights) < 1:
            highlights.append(f"Professionally curated {category.lower()} experience with attention to detail.")
        if len(highlights) < 2:
            highlights.append("Complete arrangements handled for a hassle-free and memorable journey.")
        if len(highlights) < 3:
            highlights.append("Expert guidance and support available throughout your experience.")
        
        return highlights[:3]
    
    def _create_fallback_response(self, user_input: str, database_results: List[Dict]) -> Tuple[str, Dict]:
        """Create response using ONLY verified database data with professional presentation"""
        
        logger.info("Creating fallback response with verified data...")
        
        conversational_text = f"Based on your preferences, I've found {len(database_results)} exceptional experience(s): "
        exp_names = [exp['metadata']['title'] for exp in database_results]
        conversational_text += ", ".join(exp_names) + ". Each one is specially selected from our verified database!"
        
        experience_data = {
            "conversational_intro": "I've found these verified experiences for your interests:",
            "experiences": [
                {
                    "id": exp['metadata']['id'],
                    "title": exp['metadata']['title'],
                    "category": exp['metadata']['category'],
                    "location": exp['metadata']['location'],
                    "budget": f"₹{exp['metadata']['budget']}",
                    "description": exp['metadata']['description'],
                    "similarity_score": exp['similarity_score'],
                    "why_perfect": self._generate_professional_why_perfect(exp['metadata'], user_input),
                    "highlights": self._generate_professional_highlights(exp['metadata']['description'], exp['metadata']['category'])
                }
                for exp in database_results
            ],
            "conversational_closing": "Which of these verified experiences would you like to explore first?"
        }
        
        self._save_to_memory(user_input, conversational_text, experience_data)
        return conversational_text, experience_data
    
    def _extract_json_safely(self, text: str) -> Optional[Dict]:
        """Extract JSON from text with multiple fallback methods"""
        
        json_code_block = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_code_block:
            try:
                return json.loads(json_code_block.group(1))
            except:
                pass
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        try:
            return json.loads(text)
        except:
            pass
        
        return None
    
    def _extract_user_preferences(self, user_input: str):
        """Extract and store user preferences from input"""
        input_lower = user_input.lower()
        
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
        
        budget_patterns = [r'budget.*?(\d+)', r'(\d+).*?budget', r'₹\s*(\d+)', r'rs\.?\s*(\d+)']
        for pattern in budget_patterns:
            match = re.search(pattern, input_lower)
            if match:
                self.conversation_data['user_profile']['budget_range'] = f"₹{match.group(1)}"
                break
        
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
        recent = self.conversation_data['history'][-10:]
        
        for msg in recent:
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content'][:150]
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
            summary += f"- {exp.get('title', 'Unknown')} (ID: {exp.get('id', 'Unknown')})\n"
        
        return summary
    
    def _save_to_memory(self, user_input: str, assistant_response: str, experience_data: Optional[Dict] = None):
        """Save current interaction to memory"""
        
        self.conversation_data['history'].append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.now().isoformat(),
            "experience_data": experience_data,
            "data_source": "database_verified" if experience_data else "conversational"
        })
        
        if len(self.conversation_data['history']) > MAX_CONVERSATION_HISTORY:
            self.conversation_data['history'] = self.conversation_data['history'][-MAX_CONVERSATION_HISTORY:]
        
        self.conversation_data['total_messages'] = len(self.conversation_data['history'])
        self.conversation_data['last_interaction'] = datetime.now().isoformat()
        
        if experience_data and 'experiences' in experience_data:
            for exp in experience_data['experiences']:
                exp['discussed_at'] = datetime.now().isoformat()
                if exp not in self.conversation_data['previously_discussed_experiences']:
                    self.conversation_data['previously_discussed_experiences'].append(exp)
        
        self.memory_manager.save_conversation(self.client_id, self.conversation_data)
    
    def clear_conversation_memory(self):
        """Clear conversation memory for this client"""
        self.memory_manager.delete_conversation(self.client_id)
        self.conversation_data = self.memory_manager.load_conversation(self.client_id)
        logger.info(f"Cleared conversation memory for {self.client_id}")
    
    def get_conversation_stats(self) -> Dict:
        """Get conversation statistics"""
        return self.memory_manager.get_conversation_stats(self.client_id)
    
    def get_full_conversation_history(self) -> List[Dict]:
        """Get full conversation history"""
        return self.conversation_data['history']