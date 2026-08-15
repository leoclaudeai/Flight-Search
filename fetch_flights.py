import urllib.request
import json
import time
from datetime import datetime, timedelta

HKIA_BASE_URL = 'https://www.hongkongairport.com/flightinfo-rest/rest/flights/past'
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def main():
    print("Fetching global airport locations...")
    airports_db = fetch_json('https://raw.githubusercontent.com/mwgg/Airports/master/airports.json')
    iata_coords = {v['iata']: {'name': v['name'], 'lat': v['lat'], 'lng': v['lon']} 
                   for k, v in airports_db.items() if v.get('iata') and v['iata'] != r'\N'}

    today = datetime.utcnow()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
    
    airport_routes = {}

    def process_flights(data, is_arrival, date_str):
        if not data or not isinstance(data, list) or not data[0].get('list'):
            return
        
        # Determine the weekday name (e.g. "Monday")
        day_of_week = datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')

        for item in data[0]['list']:
            remote_airports = item.get('origin') if is_arrival else item.get('destination')
            if not remote_airports:
                continue
            
            iata = remote_airports[0]
            
            # Initialize airport entry
            if iata not in airport_routes:
                apt_info = iata_coords.get(iata)
                if not apt_info:
                    continue # Skip if we don't have GPS coordinates
                
                airport_routes[iata] = {
                    'name': apt_info['name'],
                    'lat': apt_info['lat'],
                    'lng': apt_info['lng'],
                    'schedule': {day: {'arr': 0, 'dep': 0} for day in DAYS_OF_WEEK}
                }
            
            # Tally the flight
            if is_arrival:
                airport_routes[iata]['schedule'][day_of_week]['arr'] += 1
            else:
                airport_routes[iata]['schedule'][day_of_week]['dep'] += 1

    print("Fetching HKIA 7-day flight data...")
    for date_str in dates:
        print(f"Fetching data for {date_str}...")
        try:
            dep_url = f"{HKIA_BASE_URL}?date={date_str}&lang=en&cargo=false&arrival=false"
            arr_url = f"{HKIA_BASE_URL}?date={date_str}&lang=en&cargo=false&arrival=true"
            
            dep_data = fetch_json(dep_url)
            process_flights(dep_data, False, date_str)
            
            arr_data = fetch_json(arr_url)
            process_flights(arr_data, True, date_str)
        except Exception as e:
            print(f"Warning: Failed to fetch data for {date_str}: {e}")
            
        time.sleep(1) # Sleep to respect server rate limits

    # Save to a static file
    output_data = {
        'lastUpdated': today.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'routes': airport_routes
    }

    with open('flights.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    
    print(f"Success! Data saved for {len(airport_routes)} destinations.")

if __name__ == "__main__":
    main()