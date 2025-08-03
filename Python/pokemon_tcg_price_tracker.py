import requests
import pandas as pd
import os
from datetime import datetime
import time
import json

class PokemonTCGPriceTracker:
    def __init__(self, api_key=None):
        """
        Initialize the Pokemon TCG Price Tracker.
        
        Args:
            api_key (str, optional): TCGPlayer API key. If not provided, the script will
                                    attempt to use public endpoints.
        """
        self.api_key = api_key
        self.base_url = "https://api.pokemontcg.io/v2"
        self.headers = {}
        
        if self.api_key:
            self.headers["X-Api-Key"] = self.api_key
        
        self.data_folder = "pokemon_tcg_data"
        os.makedirs(self.data_folder, exist_ok=True)
    
    def search_cards(self, query, page=1, page_size=250):
        """
        Search for Pokemon cards based on a query.
        
        Args:
            query (str): Search query (e.g., 'name:Charizard')
            page (int): Page number for pagination
            page_size (int): Number of results per page
            
        Returns:
            dict: Response JSON with card data
        """
        endpoint = f"{self.base_url}/cards"
        params = {
            "q": query,
            "page": page,
            "pageSize": page_size
        }
        
        response = requests.get(endpoint, params=params, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error searching cards: {response.status_code}")
            print(response.text)
            return None
        
        return response.json()
    
    def get_card_prices(self, card_id):
        """
        Get pricing data for a specific card.
        
        Args:
            card_id (str): The card ID to fetch prices for
            
        Returns:
            dict: Price data for the card
        """
        endpoint = f"{self.base_url}/cards/{card_id}"
        
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error getting card prices: {response.status_code}")
            print(response.text)
            return None
        
        card_data = response.json().get('data', {})
        
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
    
    def save_price_data(self, card_data, filename=None):
        """
        Save card price data to a CSV file.
        
        Args:
            card_data (dict): Card price data to save
            filename (str, optional): Filename to save data to. If not provided,
                                    a default name will be used.
        """
        if not card_data or not card_data.get('prices'):
            print("No price data to save.")
            return
        
        if not filename:
            # Create a filename based on the card name
            card_name = card_data.get('name', 'unknown').replace(' ', '_').lower()
            card_set = card_data.get('set', 'unknown').replace(' ', '_').lower()
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f"{self.data_folder}/{card_name}_{card_set}_{date_str}.csv"
        
        # Flatten the price data
        flat_data = []
        
        for condition, prices in card_data['prices'].items():
            if isinstance(prices, dict):
                for price_type, price in prices.items():
                    if price is not None:
                        flat_data.append({
                            'id': card_data['id'],
                            'name': card_data['name'],
                            'set': card_data['set'],
                            'number': card_data['number'],
                            'rarity': card_data['rarity'],
                            'condition': condition,
                            'price_type': price_type,
                            'price': price,
                            'updated_at': card_data['updated_at'],
                            'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
        
        if flat_data:
            df = pd.DataFrame(flat_data)
            df.to_csv(filename, index=False)
            print(f"Price data saved to {filename}")
        else:
            print("No price data to save.")
    
    def track_cards(self, query, output_file=None):
        """
        Search for cards and track their prices.
        
        Args:
            query (str): Search query for cards to track
            output_file (str, optional): Filename to save consolidated data
        """
        search_results = self.search_cards(query)
        
        if not search_results or 'data' not in search_results:
            print("No cards found matching the query.")
            return
        
        all_price_data = []
        
        for i, card in enumerate(search_results['data']):
            print(f"Processing card {i+1}/{len(search_results['data'])}: {card.get('name')} ({card.get('id')})")
            price_data = self.get_card_prices(card['id'])
            
            if price_data:
                all_price_data.append(price_data)
                self.save_price_data(price_data)
            
            # Be nice to the API with a small delay
            time.sleep(0.5)
        
        # Save consolidated data if requested
        if output_file and all_price_data:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.data_folder}/{output_file}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(all_price_data, f, indent=2)
            
            print(f"Consolidated data saved to {filename}")
            
            # Also save as CSV for easy analysis
            flat_data = []
            for card in all_price_data:
                if card and 'prices' in card:
                    for condition, prices in card['prices'].items():
                        if isinstance(prices, dict):
                            for price_type, price in prices.items():
                                if price is not None:
                                    flat_data.append({
                                        'id': card['id'],
                                        'name': card['name'],
                                        'set': card['set'],
                                        'number': card['number'],
                                        'rarity': card['rarity'],
                                        'condition': condition,
                                        'price_type': price_type,
                                        'price': price,
                                        'updated_at': card['updated_at'],
                                        'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
            
            if flat_data:
                df = pd.DataFrame(flat_data)
                csv_filename = f"{self.data_folder}/{output_file}_{timestamp}.csv"
                df.to_csv(csv_filename, index=False)
                print(f"Consolidated CSV data saved to {csv_filename}")

# Example usage
if __name__ == "__main__":
    # Initialize tracker
    tracker = PokemonTCGPriceTracker()
    
    # Track Charizard cards
    print("Tracking Charizard cards...")
    tracker.track_cards("name:Charizard", "charizard_prices")
    
    # Track cards from a specific set
    print("\nTracking cards from Scarlet & Violet...")
    tracker.track_cards("set.name:\"Scarlet & Violet\"", "scarlet_violet_prices")
    
    # Track most expensive cards (those with high market prices)
    print("\nTracking valuable cards...")
    tracker.track_cards("tcgplayer.prices.holofoil.market:>100", "valuable_cards")