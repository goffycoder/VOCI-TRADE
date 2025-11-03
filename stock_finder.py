import pandas as pd
import os

# *** IMPORTANT ***
# Update this path to your NSE_EQ CSV file
CSV_FILE_PATH = "/Users/vrajpatel/Desktop/SBU/HCI/voice-trader/NSE_ONLY_STOCKS.csv"

class StockFinder:
    def __init__(self, csv_path=CSV_FILE_PATH):
        """
        Loads the stock master file into a pandas DataFrame.
        """
        if not os.path.exists(csv_path):
            print(f"[StockFinder]: FATAL ERROR - CSV file not found at: {csv_path}")
            raise FileNotFoundError
            
        try:
            self.df = pd.read_csv(csv_path)
            
            # --- We need two columns ---
            
            # 1. Full Company Name (e.g., "reliance industries ltd")
            if 'UNDERLYING_SYMBOL' not in self.df.columns:
                 print("[StockFinder]: FATAL ERROR - Your CSV must have an 'UNDERLYING_SYMBOL' column.")
                 raise KeyError("Missing 'UNDERLYING_SYMBOL' column in CSV")
            self.df['search_name'] = self.df['UNDERLYING_SYMBOL'].str.lower().str.replace(' limited', '').str.replace(' ltd', '').str.replace('.', '', regex=False)
            
            # 2. Security ID (e.g., "12345")
            if 'SECURITY_ID' not in self.df.columns:
                 print("[StockFinder]: FATAL ERROR - Your CSV must have a 'SECURITY_ID' column.")
                 raise KeyError("Missing 'SECURITY_ID' column in CSV")

            print(f"[StockFinder]: Loaded {len(self.df)} stocks from {csv_path}")
            
        except Exception as e:
            print(f"[StockFinder]: FATAL ERROR - Could not load or process CSV: {e}")
            raise

    def find_security_id(self, spoken_symbol: str) -> list[tuple[str, str]]:
        """
        Finds all possible matches for a spoken symbol using only the full name.
        Returns a list of tuples: (security_id, full_name)
        """
        if not spoken_symbol:
            return []
            
        search_term = spoken_symbol.lower().strip()
        
        # --- We will find ALL matches using the name and return them ---
        
        # 1. Try for an exact match on the simplified Company Name
        exact_name_match = self.df[self.df['search_name'] == search_term]
        if not exact_name_match.empty:
            # High confidence: user said the exact name. Return only this.
            row = exact_name_match.iloc[0]
            print(f"[StockFinder]: Found exact NAME match.")
            return [(str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL'])]

        # 2. If no exact match, find all partial matches in the full name
        partial_name_match = self.df[self.df['search_name'].str.contains(search_term, na=False)]
        
        if partial_name_match.empty:
            print(f"[StockFinder]: No match found for '{spoken_symbol}'.")
            return []

        # Convert the DataFrame to our list of tuples
        matches = []
        for _, row in partial_name_match.iterrows():
            matches.append((str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL']))
            
        print(f"[StockFinder]: Found {len(matches)} potential matches for '{spoken_symbol}'.")
        # Return up to 5 matches to avoid overwhelming the user
        return matches[:5]