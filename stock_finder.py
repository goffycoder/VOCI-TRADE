import pandas as pd
import os
from difflib import SequenceMatcher

CSV_FILE_PATH = "/Users/vrajpatel/Desktop/SBU/HCI/voice-trader/NSE_ONLY_STOCKS.csv"

class StockFinder:
    def __init__(self, csv_path=CSV_FILE_PATH):
        """
        Loads the stock master file into a pandas DataFrame.
        """
        if not os.path.exists(csv_path):
            print(f"[StockFinder]: FATAL ERROR - CSV file not found at: {csv_path}")
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
        try:
            self.df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_columns = ['UNDERLYING_SYMBOL', 'SECURITY_ID']
            missing_columns = [col for col in required_columns if col not in self.df.columns]
            
            if missing_columns:
                print(f"[StockFinder]: FATAL ERROR - Missing required columns: {missing_columns}")
                raise KeyError(f"Missing columns: {missing_columns}")
            
            # Create normalized search column
            self.df['search_name'] = (
                self.df['UNDERLYING_SYMBOL']
                .str.lower()
                .str.replace(' limited', '', regex=False)
                .str.replace(' ltd', '', regex=False)
                .str.replace('.', '', regex=False)
                .str.replace('-', ' ', regex=False)
                .str.strip()
            )
            
            # Create alternate search with common abbreviations
            self.df['abbrev_name'] = (
                self.df['search_name']
                .str.replace('industries', 'ind', regex=False)
                .str.replace('technologies', 'tech', regex=False)
                .str.replace('limited', '', regex=False)
            )
            
            print(f"[StockFinder]: Loaded {len(self.df)} stocks from {csv_path}")
            
        except Exception as e:
            print(f"[StockFinder]: FATAL ERROR - Could not load or process CSV: {e}")
            raise

    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, str1, str2).ratio()

    def find_security_id(self, spoken_symbol: str) -> list[tuple[str, str]]:
        """
        Finds all possible matches for a spoken symbol.
        Returns a list of tuples: (security_id, full_name)
        
        Matching strategy:
        1. Exact match on normalized name (highest priority)
        2. Exact match on abbreviated name
        3. All words present in name (partial match)
        4. Fuzzy match (similarity > 0.7)
        5. Single word match (last resort)
        """
        if not spoken_symbol:
            print("[StockFinder]: Empty search term provided.")
            return []
            
        search_term = spoken_symbol.lower().strip()
        search_words = search_term.split()
        
        print(f"[StockFinder]: Searching for '{spoken_symbol}' (words: {search_words})")
        
        # --- STRATEGY 1: Exact match on normalized name ---
        exact_match = self.df[self.df['search_name'] == search_term]
        if not exact_match.empty:
            row = exact_match.iloc[0]
            print(f"[StockFinder]: ✓ Found EXACT match: {row['UNDERLYING_SYMBOL']}")
            return [(str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL'])]
        
        # --- STRATEGY 2: Exact match on abbreviated name ---
        abbrev_match = self.df[self.df['abbrev_name'] == search_term]
        if not abbrev_match.empty:
            row = abbrev_match.iloc[0]
            print(f"[StockFinder]: ✓ Found ABBREVIATION match: {row['UNDERLYING_SYMBOL']}")
            return [(str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL'])]
        
        # --- STRATEGY 3: All words present (order-independent) ---
        if len(search_words) > 1:
            mask = pd.Series([True] * len(self.df))
            for word in search_words:
                mask = mask & self.df['search_name'].str.contains(word, na=False, regex=False)
            
            all_words_match = self.df[mask]
            if not all_words_match.empty:
                matches = [
                    (str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL'])
                    for _, row in all_words_match.iterrows()
                ]
                print(f"[StockFinder]: ✓ Found {len(matches)} ALL-WORDS matches")
                return matches[:5]
        
        # --- STRATEGY 4: Fuzzy matching (similarity > 0.7) ---
        print("[StockFinder]: Attempting fuzzy match...")
        self.df['similarity'] = self.df['search_name'].apply(
            lambda x: self._similarity_score(search_term, x)
        )
        
        fuzzy_matches = self.df[self.df['similarity'] > 0.7].sort_values('similarity', ascending=False)
        if not fuzzy_matches.empty:
            matches = [
                (str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL'])
                for _, row in fuzzy_matches.head(5).iterrows()
            ]
            print(f"[StockFinder]: ✓ Found {len(matches)} FUZZY matches (similarity > 0.7)")
            return matches
        
        # --- STRATEGY 5: Single word match (last resort) ---
        if len(search_words) == 1:
            single_word_match = self.df[
                self.df['search_name'].str.contains(search_words[0], na=False, regex=False)
            ]
            if not single_word_match.empty:
                matches = [
                    (str(row['SECURITY_ID']), row['UNDERLYING_SYMBOL'])
                    for _, row in single_word_match.iterrows()
                ]
                print(f"[StockFinder]: ✓ Found {len(matches)} PARTIAL matches")
                return matches[:5]
        
        # --- NO MATCH FOUND ---
        print(f"[StockFinder]: ✗ No match found for '{spoken_symbol}'")
        return []