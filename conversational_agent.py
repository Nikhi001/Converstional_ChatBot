# conversational_agent_app.py - Using Google Generative AI SDK directly

import os
import datetime
import requests
import wikipedia
import google.generativeai as genai
from dotenv import load_dotenv, find_dotenv
import panel as pn
import param

# Load API Key
load_dotenv(find_dotenv())
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

genai.configure(api_key=api_key)

# ========== Define Tools ==========
def get_current_temperature(latitude: float, longitude: float) -> str:
    """Fetch current temperature using Open-Meteo API for given coordinates."""
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m",
        "forecast_days": 1
    }
    try:
        response = requests.get(BASE_URL, params=params)
        if response.status_code != 200:
            return "Weather API failed."
        data = response.json()
        now = datetime.datetime.utcnow()
        times = [datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) for t in data['hourly']['time']]
        temps = data['hourly']['temperature_2m']
        index = min(range(len(times)), key=lambda i: abs(times[i] - now))
        return f"The current temperature is {temps[index]}°C"
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

def search_wikipedia(query: str) -> str:
    """Search Wikipedia for a query and return top summaries."""
    try:
        titles = wikipedia.search(query)
        summaries = []
        for title in titles[:3]:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                summaries.append(f"**{title}**\n{page.summary}")
            except:
                pass
        return "\n\n".join(summaries) if summaries else "No good result found."
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

def create_your_own(query: str) -> str:
    """Reverse the input text as a custom example tool."""
    return f"You sent: {query}. This reverses it: {query[::-1]}"

# ========== Panel Chatbot UI ==========
pn.extension()

class ConversationalBot(param.Parameterized):
    def __init__(self, **params):
        super().__init__(**params)
        self.panels = []
        self.conversation_history = []
        
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # System prompt
        self.system_prompt = """You are a helpful but slightly sassy AI assistant. 
You have access to three tools:
1. get_current_temperature(latitude, longitude) - Get weather at coordinates
2. search_wikipedia(query) - Search Wikipedia
3. create_your_own(query) - Reverse text

When user asks to use these tools, you can call them. Keep responses concise and friendly."""

    def process_query(self, query: str) -> str:
        """Process user query with Gemini and tools."""
        try:
            # Build conversation context
            messages = []
            for msg in self.conversation_history:
                messages.append(f"{msg['role']}: {msg['content']}")
            messages.append(f"user: {query}")
            
            conversation_text = "\n".join(messages)
            
            # Send to Gemini
            full_prompt = f"{self.system_prompt}\n\nConversation:\n{conversation_text}"
            response = self.model.generate_content(full_prompt)
            
            answer = response.text if response.text else "I couldn't generate a response."
            
            # Check if assistant wants to use tools
            if "temperature" in query.lower() and "latitude" in query.lower():
                # Example: Extract coordinates from query (simplified)
                try:
                    parts = query.split()
                    for i, part in enumerate(parts):
                        if part.lower() == "latitude" and i+1 < len(parts):
                            lat = float(parts[i+1].rstrip(","))
                            lon = float(parts[i+3].rstrip(",")) if i+3 < len(parts) else 0
                            temp_result = get_current_temperature(lat, lon)
                            answer = f"{answer}\n\n📍 Tool Result: {temp_result}"
                except:
                    pass
            
            elif "wikipedia" in query.lower():
                search_query = query.replace("wikipedia", "").replace("search", "").strip()
                if search_query:
                    wiki_result = search_wikipedia(search_query)
                    answer = f"{answer}\n\n📖 Wikipedia Result: {wiki_result}"
            
            elif "reverse" in query.lower():
                reverse_text = query.replace("reverse", "").strip()
                if reverse_text:
                    reverse_result = create_your_own(reverse_text)
                    answer = f"{answer}\n\n🔄 Reversed: {reverse_result}"
            
            return answer
            
        except Exception as e:
            return f"Error: {str(e)}"

    def interact(self, query):
        if not query:
            return
        
        # Get response
        answer = self.process_query(query)
        
        # Store in history
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": answer})
        
        # Keep only last 10 messages for context
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        # Display
        self.panels.extend([
            pn.Row('👤 You:', pn.pane.Markdown(query, width=500)),
            pn.Row('🤖 Bot:', pn.pane.Markdown(answer, width=500, styles={"background-color": "#f0f0f0"}))
        ])
        
        return pn.WidgetBox(*self.panels, scroll=True)


# Create bot and UI
cb = ConversationalBot()
inp = pn.widgets.TextInput(placeholder='Ask me anything...')
conversation = pn.bind(cb.interact, inp)

tab = pn.Column(
    pn.Row(inp),
    pn.layout.Divider(),
    pn.panel(conversation, loading_indicator=True, height=400),
    pn.layout.Divider()
)

dashboard = pn.Column(
    pn.Row(pn.pane.Markdown('# 🧠 Conversational Agent Bot')),
    pn.Tabs(('Chat', tab))
)

dashboard.servable()