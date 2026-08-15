import urllib.request
import json
import time
from datetime import datetime, timedelta

HKIA_BASE_URL = 'https://www.hongkongairport.com/flightinfo-rest/rest/flights/past'

# Map weekdays to the 2-letter codes shown in the screenshot
DAYS_MAP = {
    'Sunday': 'su',
    'Monday': 'mo',
    'Tuesday': 'tu',
    'Wednesday': 'we',
    'Thursday': 'th',
    'Friday': 'fr',
    'Saturday': 'sa'
}
DAY_KEYS = ['su', 'mo', 'tu', 'we', 'th', 'fr', 'sa']

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def main():
    print("Fetching global airport locations...")
    airports_db = fetch_json('https://raw.githubusercontent.com/mwgg/Airports/master/airports.json')
    iata_coords = {}
    for k, v in airports_db.items():
        if v.get('iata') and v['iata'] != r'\N':
            iata_coords[v['iata']] = {
                'name': v['name'],
                'city': v.get('city', v['name']),
                'lat': v['lat'],
                'lng': v['lon']
            }

    today = datetime.utcnow()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
    
    airport_routes = {}

    def process_flights(data, is_arrival, date_str):
        flight_list = []
        if isinstance(data, list) and len(data) > 0 and 'list' in data[0]:
            flight_list = data[0]['list']
        elif isinstance(data, dict) and 'list' in data:
            flight_list = data['list']

        if not flight_list:
            return
        
        day_key = DAYS_MAP[datetime.strptime(date_str, '%Y-%m-%d').strftime('%A')]

        for item in flight_list:
            remote_airports = item.get('origin') if is_arrival else item.get('destination')
            if not remote_airports:
                continue
            
            iata = remote_airports[0]
            if iata not in iata_coords:
                continue

            apt_info = iata_coords[iata]
            if iata not in airport_routes:
                airport_routes[iata] = {
                    'name': apt_info['name'],
                    'city': apt_info['city'],
                    'lat': apt_info['lat'],
                    'lng': apt_info['lng'],
                    'airlines': {}
                }

            # Extract airline and flight details
            flights = item.get('flight', [])
            if not flights:
                continue
            
            primary_flight = flights[0]
            airline_name = primary_flight.get('airline', 'Other Airline')
            flight_no = primary_flight.get('no', 'N/A')
            flight_time = item.get('time', 'N/A')
            status = item.get('status', 'Scheduled')

            airlines_dict = airport_routes[iata]['airlines']
            if airline_name not in airlines_dict:
                airlines_dict[airline_name] = {
                    'days': {d: [] for d in DAY_KEYS}
                }

            # Deduplicate entries for the same flight
            existing = airlines_dict[airline_name]['days'][day_key]
            if not any(f['no'] == flight_no and f['time'] == flight_time for f in existing):
                existing.append({
                    'no': flight_no,
                    'time': flight_time,
                    'type': 'Arrival' if is_arrival else 'Departure',
                    'status': status
                })

    print("Fetching HKIA 7-day flight schedule...")
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
            print(f"Warning: Failed for {date_str}: {e}")
            
        time.sleep(0.8)

    output_data = {
        'lastUpdated': today.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'routes': airport_routes
    }

    with open('flights.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Success! Saved detailed schedules for {len(airport_routes)} airports.")

if __name__ == "__main__":
    main()
