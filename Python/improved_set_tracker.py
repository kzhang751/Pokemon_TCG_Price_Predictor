from pokemon_tcg_price_tracker import PokemonTCGPriceTracker
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
import time
import re
import json
import requests
import sys

# Number of seconds to wait between API requests to avoid rate limiting
DEFAULT_RATE_LIMIT_DELAY = 1.0

class SetTracker:
    def __init__(self, api_key=None, rate_limit_delay=DEFAULT_RATE_LIMIT_DELAY):
        """
        Initialize the Set Tracker.
        
        Args:
            api_key (str, optional): API key for Pokemon TCG API
            rate_limit_delay (float): Seconds to wait between API calls
        """
        self.tracker = PokemonTCGPriceTracker(api_key)
        self.rate_limit_delay = rate_limit_delay
        self.base_url = self.tracker.base_url
        self.headers = self.tracker.headers
        
    def safe_api_call(self, url, params=None, max_retries=3, backoff_factor=2):
        """
        Makes an API call with rate limit handling and retries.
        
        Args:
            url: API endpoint
            params: Query parameters
            max_retries: Maximum number of retries on failure
            backoff_factor: Multiplier for wait time between retries
            
        Returns:
            Response JSON or None on failure
        """
        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(url, params=params, headers=self.headers)
                
                # Handle different status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = self.rate_limit_delay * (backoff_factor ** retries)
                    print(f"Rate limited. Waiting for {wait_time:.1f} seconds before retry...")
                    time.sleep(wait_time)
                    retries += 1
                    continue
                else:
                    print(f"API error: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"Request error: {str(e)}")
                retries += 1
                if retries <= max_retries:
                    wait_time = self.rate_limit_delay * (backoff_factor ** retries)
                    print(f"Retrying in {wait_time:.1f} seconds... (Attempt {retries}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    return None
                    
            # Always add delay between requests to avoid rate limiting
            time.sleep(self.rate_limit_delay)
                
        return None

    def get_all_set_names(self):
        """
        Get a list of all available set names from the API to ensure we're using correct formatting.
        Uses pagination to get all sets.
        
        Returns:
            List of properly formatted set names and their details
        """
        print("Fetching all available set names from the API...")
        all_sets = []
        page = 1
        
        while True:
            endpoint = f"{self.base_url}/sets"
            params = {"page": page, "pageSize": 250}
            
            response_data = self.safe_api_call(endpoint, params)
            
            if not response_data or 'data' not in response_data:
                if page == 1:
                    print("Error: Could not retrieve available sets from the API.")
                    return []
                else:
                    # We've reached the end of pagination
                    break
            
            sets_data = response_data.get('data', [])
            if not sets_data:
                break
                
            all_sets.extend(sets_data)
            print(f"Fetched page {page} of sets data ({len(sets_data)} sets)")
            
            # Check if we've reached the last page
            if 'count' in response_data and 'totalCount' in response_data:
                if response_data['count'] * page >= response_data['totalCount']:
                    break
                    
            page += 1
            
        print(f"Retrieved {len(all_sets)} total sets")
        
        # Extract just the names for easy matching
        set_names = [s.get('name') for s in all_sets]
        return set_names, all_sets

    def find_closest_set_name(self, target_name, available_sets):
        """
        Find the closest matching set name from the available sets.
        
        Args:
            target_name: The set name we're looking for
            available_sets: List of available set names from the API
            
        Returns:
            The closest matching set name
        """
        # First try exact match
        if target_name in available_sets:
            return target_name
        
        # Try case-insensitive match
        for s in available_sets:
            if s.lower() == target_name.lower():
                return s
        
        # Check if "Black Star Promos" needs special handling
        if "Black Star Promos" in target_name:
            for s in available_sets:
                # Look for variations like "—Black Star Promos", "- Black Star Promos", etc.
                if target_name.split("Black Star")[0].strip() in s and "Black Star Promos" in s:
                    return s
        
        # Look for partial matches (if target is contained within an actual set name)
        matches = [s for s in available_sets if target_name.lower() in s.lower()]
        if matches:
            return matches[0]  # Return the first match
            
        # Try more flexible matching - split on common separators and match key terms
        target_terms = re.split(r'[-—_&\s]+', target_name.lower())
        
        best_match = None
        most_terms_matched = 0
        
        for s in available_sets:
            set_terms = re.split(r'[-—_&\s]+', s.lower())
            matched_terms = sum(1 for term in target_terms if term in set_terms)
            
            if matched_terms > most_terms_matched:
                most_terms_matched = matched_terms
                best_match = s
        
        return best_match

    def search_cards(self, query, max_pages=10):
        """
        Search for cards with handling for pagination and rate limits.
        
        Args:
            query: The search query
            max_pages: Maximum number of pages to retrieve
            
        Returns:
            List of all card data across all pages
        """
        all_cards = []
        page = 1
        
        while page <= max_pages:
            endpoint = f"{self.base_url}/cards"
            params = {"q": query, "page": page, "pageSize": 250}
            
            response_data = self.safe_api_call(endpoint, params)
            
            if not response_data or 'data' not in response_data:
                break
                
            page_cards = response_data.get('data', [])
            if not page_cards:
                break
                
            all_cards.extend(page_cards)
            print(f"Fetched page {page} ({len(page_cards)} cards)")
            
            # Check if we've reached the last page
            if 'count' in response_data and 'totalCount' in response_data:
                if page_cards and len(all_cards) >= response_data['totalCount']:
                    break
                    
            page += 1
            
        return all_cards

    def get_card_prices(self, card_id):
        """
        Get pricing data for a specific card with rate limit handling.
        
        Args:
            card_id: The card ID
            
        Returns:
            Card price data or None on failure
        """
        endpoint = f"{self.base_url}/cards/{card_id}"
        response_data = self.safe_api_call(endpoint)
        
        if not response_data or 'data' not in response_data:
            return None
            
        card_data = response_data.get('data', {})
        
        # Extract the pricing data
        if 'tcgplayer' in card_data and 'prices' in card_data['tcgplayer']:
            return {
                'id': card_id,
                'name': card_data.get('name', ''),
                'set': card_data.get('set', {}).get('name', ''),
                'number': card_data.get('number', ''),
                'rarity': card_data.get('rarity', ''),
                'prices': card_data['tcgplayer']['prices'],
                'updated_at': card_data['tcgplayer'].get('updatedAt', '')
            }
        
        return None

    def track_multiple_sets_to_csv(self, set_names, output_file_prefix="combined_sets"):
        """
        Track all cards from multiple specified sets and save to a single CSV file.
        
        Args:
            set_names: List of set names (e.g., ["Jungle", "Base Set", "Brilliant Stars"])
            output_file_prefix: Prefix for output filename
        
        Returns:
            DataFrame containing all price data from all sets
        """
        # Get all available set names for matching
        available_set_names, all_sets_data = self.get_all_set_names()
        
        if not available_set_names:
            print("Error: Could not retrieve available sets from the API.")
            return None
            
        # Save the full sets data for reference
        data_folder = "pokemon_tcg_data"
        os.makedirs(data_folder, exist_ok=True)
        sets_filename = f"{data_folder}/all_set_data.json"
        with open(sets_filename, 'w') as f:
            json.dump(all_sets_data, f, indent=2)
        print(f"Saved complete set data to: {sets_filename}")
            
        print(f"Found {len(available_set_names)} sets in the API.")
        
        # Initialize list to store all price data
        all_price_data = []
        
        # Dictionary to map user provided set names to API set names
        set_name_mapping = {}
        
        # Process each set
        for set_name in set_names:
            print(f"\n{'='*50}")
            print(f"Finding matching set name for '{set_name}'...")
            
            # Find the closest matching set name
            matched_set = self.find_closest_set_name(set_name, available_set_names)
            
            if not matched_set:
                print(f"No matching set found for '{set_name}'. Skipping to next set.")
                set_name_mapping[set_name] = "Not found"
                continue
                
            print(f"Matched '{set_name}' to API set name '{matched_set}'")
            set_name_mapping[set_name] = matched_set
            
            print(f"Searching for all cards in the {matched_set} set...")
            print(f"{'='*50}")
            
            # Format the set name for the query
            query = f'set.name:"{matched_set}"'
            
            # Get all cards with pagination handling
            total_cards = self.search_cards(query)
            
            if not total_cards:
                print(f"No cards found in the {matched_set} set. Skipping to next set.")
                continue
            
            print(f"Found {len(total_cards)} cards in the {matched_set} set.")
            
            # Process each card in the set
            for i, card in enumerate(total_cards):
                print(f"Processing card {i+1}/{len(total_cards)}: {card.get('name')} ({card.get('id')})")
                
                # Get price data for the card
                price_data = self.get_card_prices(card['id'])
                
                if price_data and 'prices' in price_data:
                    # Flatten the pricing data and add to our list
                    for condition, prices in price_data['prices'].items():
                        if isinstance(prices, dict) and 'market' in prices and prices['market'] is not None:
                            all_price_data.append({
                                'id': price_data['id'],
                                'name': price_data['name'],
                                'set': price_data['set'],
                                'number': price_data['number'],
                                'rarity': price_data['rarity'],
                                'condition': condition,
                                'price': prices['market'],  # Only including market price
                                'updated_at': price_data['updated_at'],
                                'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
        
        # Save all price data to a single CSV file
        if all_price_data:
            # Save the set name mapping
            mapping_filename = f"{data_folder}/{output_file_prefix}_set_mapping.json"
            with open(mapping_filename, 'w') as f:
                json.dump(set_name_mapping, f, indent=2)
            print(f"\nSaved set name mapping to: {mapping_filename}")
            
            # Create DataFrame from the price data
            df = pd.DataFrame(all_price_data)
            
            # Extract numeric part for proper sorting
            def extract_number(num_str):
                if pd.isna(num_str):
                    return float('inf')  # Put NaN values at the end
                
                # Extract digits from the string
                match = re.search(r'(\d+)', str(num_str))
                if match:
                    return int(match.group(1))
                return float('inf')  # Non-numeric strings at the end
            
            # Extract letter part for secondary sorting
            def extract_letter(num_str):
                if pd.isna(num_str):
                    return ''
                
                # Extract non-digit part
                match = re.search(r'([a-zA-Z]+)', str(num_str))
                if match:
                    return match.group(1)
                return ''
            
            # Add sorting columns
            df['numeric_part'] = df['number'].apply(extract_number)
            df['alpha_part'] = df['number'].apply(extract_letter)
            
            # Sort by set first, then numeric part, then alpha part, then condition
            df = df.sort_values(['set', 'numeric_part', 'alpha_part', 'condition'])
            
            # Remove temporary sorting columns
            df = df.drop(columns=['numeric_part', 'alpha_part'])
            
            # Create timestamp for filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save detailed CSV
            filename = f"{data_folder}/{output_file_prefix}_{timestamp}.csv"
            df.to_csv(filename, index=False)
            print(f"\nSuccessfully saved all price data ({len(all_price_data)} entries) from {len(set_names)} sets to a single CSV file:")
            print(f"{filename}")
            
            # Create a pivot table for easier analysis (just condition since we only have market prices)
            pivot_df = df.pivot_table(
                index=['set', 'number', 'name', 'rarity'], 
                columns=['condition'], 
                values='price'
            ).reset_index()
            
            # Save pivot table to CSV
            pivot_filename = f"{data_folder}/{output_file_prefix}_pivot_{timestamp}.csv"
            pivot_df.to_csv(pivot_filename)
            print(f"Also saved a pivot table format to: {pivot_filename}")
            
            return df
        else:
            print(f"No price data found for any cards in the specified sets.")
            return None

def main():
    """Main function to run the script with command line arguments."""
    # You could add argparse here to accept API key from command line
    api_key = os.getenv("API_KEY")
    rate_limit_delay = 1.5  # Seconds between API calls to avoid rate limiting
    
    sets_to_track = [
        "151"]
    
    load_dotenv()
    
    # Initialize the tracker
    tracker = SetTracker(api_key=api_key, rate_limit_delay=rate_limit_delay)
    
    # Track all specified sets
    tracker.track_multiple_sets_to_csv(sets_to_track, "SAMPLE_TRACKED_SETS")

if __name__ == "__main__":
    main()