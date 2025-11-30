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
    raise ValueError("GOOGLE_API_KEY not found in .env file, check your API Key")
genai.configure(api_key=api_key)

# ========== Define Tools ==========
def search_wikipedia(query: str) -> str:
    """Search wikipedia for a query and return top summaries."""
    try:
        titles = wikipedia.search(query)
        summaries = []
        for title in titles[:3]:
            try:
                page = wikipedia.page(title,auto_suggest=False)
                summaries.append(f"**{title}**\n{page.summary}")
            except:
                 pass
        return "\n\n".join(summaries) if summaries else "No good result found."
    except Exception as e:
        return f"Error searching wikipedia: {str(e)}"
    
    #========== Panel Interface ==========
pn.extension()
class ConversationalBot(param.Parameterized):
    def __init__(self, **params):
        super().__init__(**params)
        self.panels = []
        self.conversation_history = []

        self.model = genai.GenerativeModel('gemini-2.5-pro')

        #System prompt
        self.system_prompt = """You are a helpful assistant that can use tools to answer user queries.
        you have access to the following tools:
        1. search_wikipedia: useful for when you need to look up information on wikipedia
        when user asks to use these tools, you can call them. Keep responses concise and friendly."""
#=====================process query function=========================
    def process_query(self, query: str) -> str:
        """Proess user query with Gemini and tools."""
        try:
            # Build conversation context
            messages = []
            for msg in self.conversation_history:
                messages.append(f"{msg['role']}: {msg['content']}")
            messages.append(f'user: {query}')

            conversation_text = "\n".join(messages)

            # send to Gemini
            full_prompt = f"{self.system_prompt}\n\nConversation:\n{conversation_text}"
            response = self.model.generate_content(full_prompt)
            answer = response.text if response.text else "I couldn't generate a response."

            # wikipedia tool call handling
            if "wikipedia" in answer.lower():
                search_query = query.split("wikipedia","").replace("search","").strip()
                wiki_result = search_wikipedia(search_query)
                answer = f"{answer}\n\n wikipedia result:\n{wiki_result}"

            return answer
        except Exception as e:
            return f"Error processing query: {str(e)}"
#=========interactive UI=========
    def interact(self,query):
        if not query:
            return
        
        #Get response
        answer = self.process_query(query)

        #store conversation history
        self.conversation_history.append({"role":"user","content":query})
        self.conversation_history.append({"role":"assistant","content":answer})
        
        #keep only last 10 exchanges
        if len(self.conversation_history)>10:
            self.conversation_history = self.conversation_history[-10:]

        #Display conversation
        self.panels.extend([
            pn.Row('You:',pn.pane.Markdown(query, width=600)),
            pn.Row('Bot:',pn.pane.Markdown(answer, width= 600),styles = {"background-color":"#f0f0f0"})
        ])

        return pn.WidgetBox(*self.panels, scroll=True)

#Create bot and UI
cb = ConversationalBot()
inp = pn.widgets.TextInput(placeholder='Enter your message here...', width=600)
conversation = pn.bind(cb.interact, inp)

tab = pn.Column(
    pn.Row(inp),
    pn.layout.Divider(),
    pn.panel(conversation, loading_indicator=True, height=400),
    pn.layout.Divider()
)
dashboard = pn.Column(
    pn.Row(pn.pane.Markdown('# Conversational Agent Bot')),
    pn.Tabs(('Chat', tab))
)   
dashboard.servable()