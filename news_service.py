import feedparser
import urllib.parse

def get_latest_market_news(query: str = "Indian Stock Market") -> list[str]:
    """
    Fetches top 5 headlines from Google News RSS.
    Returns a list of strings to send to Gemini.
    """
    print(f"[News]: Fetching news for '{query}'...")
    
    # Encode query for URL
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(rss_url)
        headlines = []
        
        # Only take top 5 to save Gemini tokens
        for entry in feed.entries[:5]:
            title = entry.title
            # Google news titles often look like "Headline - Source", clean it up if needed
            headlines.append(title)
            
        print(f"[News]: Found {len(headlines)} headlines.")
        return headlines
    except Exception as e:
        print(f"[News]: Error fetching news: {e}")
        return []