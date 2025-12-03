import google.generativeai as genai
import json

# Import your existing data fetchers
from news_service import get_latest_market_news
# We will pass the dhan instance dynamically or import if singleton

class MarketChatEngine:
    def __init__(self, gemini_model, dhan_handler):
        self.model = gemini_model
        self.dhan = dhan_handler

    def get_data_requirements(self, user_query: str) -> dict:
        """
        Ask LLM: What live data do I need to answer this conversational query?
        """
        prompt = f"""
        You are an AI assistant analyzing a stock market conversation.
        User Query: "{user_query}"

        Determine if you need real-time data to answer intelligently.
        
        OUTPUT JSON FORMAT:
        {{
            "needs_price": boolean,
            "needs_news": boolean,
            "symbol": "string" (e.g. "RELIANCE", "TATASTEEL" or null),
            "topic": "string" (e.g. "Indian IT Sector" or null)
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "")
            return json.loads(text)
        except:
            return {"needs_price": False, "needs_news": False}

    def generate_reply(self, user_query: str, history: list = []) -> str:
        # 1. Analyze what data is needed
        reqs = self.get_data_requirements(user_query)
        context_data = []

        # 2. Fetch Data (if needed)
        if reqs.get("needs_price") and reqs.get("symbol"):
            # Use existing logic to find security ID (simplified here, ideally reuse StockFinder)
            # For now, we assume we can pass the symbol name to your text generator
            context_data.append(f"System Note: User is asking about {reqs['symbol']}.")
            
            # In a real scenario, you'd use stock_finder here to get the ID, then dhan.get_live_price
            # letting the LLM know we can't fetch price without ID is handled in the final prompt
        
        if reqs.get("needs_news"):
            topic = reqs.get("topic") or reqs.get("symbol") or "Indian Stock Market"
            headlines = get_latest_market_news(topic)
            if headlines:
                context_data.append(f"Latest Headlines for {topic}: {'; '.join(headlines)}")

        # 3. Generate Conversational Response
        context_str = "\n".join(context_data)
        
        final_prompt = f"""
        You are a witty, intelligent stock market trading companion.
        
        CONTEXT DATA (Real-time):
        {context_str}

        USER QUERY: "{user_query}"

        INSTRUCTIONS:
        - Answer the user naturally.
        - If you have news/context, use it to explain "Why".
        - Keep it brief (2-3 sentences) because this is a voice conversation.
        - If the user asks for an opinion, give a balanced view based on the news, but add "Do your own research."
        - Do not read the raw news headlines; synthesize them.

        ANSWER:
        """
        
        response = self.model.generate_content(final_prompt)
        return response.text.strip()