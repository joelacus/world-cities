import zipfile
import requests
import json
import csv
import os
import signal
import sys
import time
import logging
import time
import argparse

# GetWorldCities
# Author https://github.com/joelacus
version = 1.1

# ArgumentParser
parser = argparse.ArgumentParser(prog='python get_world_cities.py',description="Generate a custom csv/json file of all the cities in the world.")

# Define your arguments
parser.add_argument("-c", "--convert", help="Convert file.csv to file.json, or vice versa.")
parser.add_argument("-v", "--version", action="store_true", help="Show version number.")
parser.add_argument("-l", "--log", action="store_true", help="Save a log file in the same directory as the script.")
parser.add_argument("-dr", "--disable_reference", action="store_true", help="Don't use a preloaded reference file to save time, but instead query geocode.maps.co api for every request. This will take a very long time.")
parser.add_argument("-drd", "--disable_reference_download", action="store_true", help="Don't download the reference file if it already exists in the directory. It will be downloaded if it does not exist.")
parser.add_argument("-p1", "--preset1", action="store_true", help="Pre-select options to save a CSV file with country, place name, latitude, longitude.")
parser.add_argument("-p2", "--preset2", action="store_true", help="Pre-select options to save a CSV file with country, US states, place name, latitude, longitude.")
parser.add_argument("-p3", "--preset3", action="store_true", help="Pre-select options to save a CSV file with country, states for duplicated place names, counties for duplicated place names, place name, latitude, longitude.")
parser.add_argument("-p4", "--preset4", action="store_true", help="Pre-select options to save a CSV file with country, state, county, name, latitude, longitude. (Reference File)")

# Parse the command-line arguments
args = parser.parse_args()

log = False
disableReference = False
disableReferenceDownload = False
preset = None

# Arg Convert
if args.convert:
    filename = os.path.splitext(args.convert)[0]
    ext = os.path.splitext(args.convert)[1]

    if ext == '.csv':
        # Read the CSV file
        with open(args.convert, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            # Convert to JSON
            data = []
            for row in csv_reader:
                data.append(row)

        # Write JSON data to a file
        with open(f'{filename}.json', 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2)

    if ext == '.json':
        # Load the JSON data from the input file
        with open(args.convert, 'r') as json_file:
            json_data = json.load(json_file)

        # Extract column headers from the first dictionary in the JSON data
        headers = json_data[0].keys()

        # Open the CSV file for writing
        with open(f'{filename}.csv', 'w', newline='') as csv_file:
            # Create a CSV writer and write the headers
            csv_writer = csv.DictWriter(csv_file, fieldnames=headers)
            csv_writer.writeheader()

            # Write each dictionary in the JSON data as a row in the CSV
            for row in json_data:
                csv_writer.writerow(row)
    sys.exit(0)

# Arg Version
if args.version:
    print(f'GetWorldCities {version}')
    sys.exit(0)

# Arg Log
if args.log:
    log = True

# Arg Disable Reference File
if args.disable_reference:
    disableReference = True

# Arg Disable Reference File Download
if args.disable_reference_download:
    disableReferenceDownload = True

# Arg Preset
if args.preset1:
    preset = 1
if args.preset2:
    preset = 2
if args.preset3:
    preset = 3
if args.preset4:
    preset = 4


# Logging config
if log:
    logging.basicConfig(
        filename='get_world_cities.log',
        encoding='utf-8',
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)

# File downloader
def download_file(url, save_path):
    print(f"> Downloading {save_path}")
    try:
        response = requests.get(url)
        try:
            with open(save_path, 'wb') as file:
                file.write(response.content)
            logging.info(f"Downloaded {url} to {save_path}.")
        except IOError as e:
            logging.error(f"Could not save {save_path}. {e}. Abort!")
            sys.exit(0)
    except requests.exceptions.RequestException as e:
        logging.error(f"Download failed from {url}. {e}. Abort!")
        sys.exit(0)

# Download reference file (this preloads state and county data which would otherwise take a long time to get from geocode.maps.co api)
ref_file = 'world_cities_(including_all_states_and_counties).csv'
global ref_data
ref_data = None
def download_reference_file():
    if disableReferenceDownload == False:
        download_file("https://raw.githubusercontent.com/joelacus/world-cities/main/world_cities_(including_all_states_and_counties).csv", "world_cities_(including_all_states_and_counties).csv")
    if os.path.exists(ref_file):
        try:
            with open(ref_file, 'r', encoding='utf-8') as csv_file:
                print(f"> Reading {ref_file}")
                csv_reader = csv.DictReader(csv_file)
                # Convert CSV to object
                global ref_data
                ref_data = []
                for row in csv_reader:
                    ref_data.append(row)
        except IOError as e:
            logging.error(f"Could not read {ref_file} into object. {e}")
    else:
        logging.info(f"{ref_file} not found")
        print(f"> {ref_file} not found")
        download_file("https://raw.githubusercontent.com/joelacus/world-cities/main/world_cities_(including_all_states_and_counties).csv", "world_cities_(including_all_states_and_counties).csv")
        download_reference_file()

# Check Geocode API Key
api_key = None
def checkGeocodeKey():
    global api_key
    if api_key is not None:
        return api_key
    else:
        if os.path.exists('geocode_maps_api_key.txt'):
            try:
                with open('geocode_maps_api_key.txt', 'r') as geocode_api_key_file:
                    api_key = geocode_api_key_file.readline().strip()
            except:
                logging.error(f"Could not read {geocode_api_key_file} into object. {e}")
                api_key = enter_geocode_api_key()
        else:
            api_key = enter_geocode_api_key()
    return api_key

# Ask For Geocode API Key If Required
def enter_geocode_api_key():
    print("> Geocode API Key is required.")
    api_key = input("? Enter Key: ")
    if get_yes_or_no("? Save the key in the current directory to save you entering it next time?: "):
        with open('geocode_maps_api_key.txt', 'w') as file:
            file.write(api_key)
    return api_key

# GeoCode API Lookup
prev_lat = None
prev_lng = None
county = ''
state = ''
lookup_count = 0
def lookUpGeo(lat,lng,key):
    # Get Geocode API Key
    api_key = checkGeocodeKey()

    #
    global prev_lat
    global prev_lng
    global state
    global county
    global lookup_count
    if lat == prev_lat and lng == prev_lng and key == 'county':
        print(f"> Remembering county from state query " + lat + "," + lng)
        return county
    else:
        prev_lat = lat
        prev_lng = lng

        # Geocode limits free accounts to 1 request per second 
        time.sleep(1)

        # Fetch
        print("> Fetching "+key+" for "+lat+","+lng)
        logging.info("Fetching "+key+" for "+lat+","+lng)
        geocodeUrl = f"https://geocode.maps.co/reverse?lat={lat}&lon={lng}&api_key={api_key}"
        try:
            lookup_count += 1
            response = requests.get(geocodeUrl)
            response.raise_for_status()
            geocodeData = response.json()
            if 'state' in geocodeData['address']:
                logging.info(geocodeData['address']['state'])
                state = geocodeData['address']['state']
            if 'county' in geocodeData['address']:
                logging.info(geocodeData['address']['county'])
                county = geocodeData['address']['county']
            
            if key == 'state':
                return state

            if key == 'county':
                return county
            
        except Exception as e:
            logging.error(f"Querying {lat},{lng} {key} failed. {e}")

            # Retry up to 5 times
            for _ in range(5):
                print(f"> Retrying in 5 seconds...")
                time.sleep(5)
                try:
                    lookup_count += 1
                    response = requests.get(geocodeUrl)
                    response.raise_for_status()
                    geocodeData = response.json()
                    if key in geocodeData['address']:
                        return geocodeData['address'][key]
                    print(f"> Retry for {lat},{lng} {key} succeded.")
                    logging.info(f"> Retry for {lat},{lng} {key} succeded.")
                    break

                except Exception as e:
                    print(f"> Retry failed:", str(e))
                    continue

# Define a dictionary to map full state names to abbreviations for all US states
state_abbreviations = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY',
    'District of Columbia': 'DC'
}

# Yes/No prompt
def get_yes_or_no(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response.lower() == 'yes' or response.lower() == 'y':
            return True
        elif response.lower() == 'no' or response.lower() == 'n':
            return False
        else:
            print("> Please enter '(y)es' or '(n)o'.")

# Population threshold prompt
def get_pop_threshold(prompt):
    while True:
        response = input(prompt).strip()
        if response == '1000':
            return '1000'
        elif response == '5000':
            return '5000'
        elif response == '15000':
            return '15000'
        else:
            print("> Please enter '1000', '5000', or '15000'.")

# File format prompt
def get_format(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response == 'json':
            return 'json'
        elif response == 'csv':
            return 'csv'
        else:
            print("> Please enter 'json' or 'csv'.")

# Create ref data for dupes
def create_ref_data_for_dupes(file,country_list_for_dupes):
    # Optimised list of country and place names
    list_country_place = list()
    for line in file:
        line_data2 = line.decode('utf-8').strip().split('\t')
        value = (line_data2[8],line_data2[1])
        list_country_place.append(value)
    # Optimise reference data for states and counties
    ref_data_states = {}
    ref_data_counties = {}
    if disableReference == False:
        if not ref_data:
            download_reference_file()
        for item in ref_data:
            if item['country'].lower() in country_list_for_dupes.lower().split(',') or country_list_for_dupes == '':
                lat = item['lat']
                lng = item['lng']
                name = item['name']
                ref_data_states[(lat, lng, name)] = item
                ref_data_counties[(lat, lng, name)] = item
    return list_country_place,ref_data_states,ref_data_counties

# Process the cities.txt file and create JSON objects
def process_text_file(zip_file_path, text_file_name):
    json_data = []

    # Open cities zipfile
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        with zip_ref.open(text_file_name) as f:
            file = f.readlines()

            # Count total number of items
            totalItems = sum(1 for _ in file)
            count = 0

            # Init vars
            global include_country_code
            global include_country_name
            global include_state
            global include_county
            global include_state_for_dupe
            global include_county_for_dupe
            global include_altnames
            global include_timezone
            global include_population
            global include_altitude

            # If preset argument is used, set preset defaults, otherwise, prompt user
            if (preset == 4):
                include_country_code = True
                include_country_name = False
                include_altnames = False
                include_state = True
                country_list_for_states = ''
                if disableReference == False:
                    download_reference_file()
                    ref_data_states = {}
                    for item in ref_data:
                        lat = item['lat']
                        lng = item['lng']
                        name = item['name']
                        ref_data_states[(lat, lng, name)] = item
                abbreviate_us_states = False
                include_county = True
                country_list_for_counties = ''
                if disableReference == False:
                    ref_data_counties = {}
                    for item in ref_data:
                        lat = item['lat']
                        lng = item['lng']
                        name = item['name']
                        ref_data_counties[(lat, lng, name)] = item
                include_state_for_dupe = False
                include_county_for_dupe = False
                include_timezone = False
                include_population = False
                include_altitude = False
            elif (preset == 1):
                include_country_code = True
                include_country_name = False
                include_altnames = False
                include_state = False
                country_list_for_states = None
                include_county = False
                country_list_for_counties = None
                include_state_for_dupe = False
                include_county_for_dupe = False
                include_timezone = False
                include_population = False
                include_altitude = False
            elif (preset == 2):
                include_country_code = True
                include_country_name = False
                include_altnames = False
                include_state = True
                country_list_for_states = 'us'
                if disableReference == False:
                    download_reference_file()
                    ref_data_states = {}
                    for item in ref_data:
                        if item['country'].lower() in 'us':
                            lat = item['lat']
                            lng = item['lng']
                            name = item['name']
                            ref_data_states[(lat, lng, name)] = item
                abbreviate_us_states = True
                include_county = False
                country_list_for_counties = None
                include_state_for_dupe = False
                include_county_for_dupe = False
                include_timezone = False
                include_population = False
                include_altitude = False
            elif (preset == 3):
                include_country_code = True
                include_country_name = False
                include_altnames = False
                include_state = False
                country_list_for_states = None
                include_county = False
                country_list_for_counties = None
                include_state_for_dupe = True
                abbreviate_us_states = False
                include_county_for_dupe = True
                country_list_for_dupes = ''
                list_country_place,ref_data_states,ref_data_counties = create_ref_data_for_dupes(file,country_list_for_dupes)
                include_timezone = False
                include_population = False
                include_altitude = False
            else:
                # Include country codes?
                if get_yes_or_no("? Include ISO-3166 2-letter country codes ('GB'): "):
                    include_country_code = True
                else:
                    include_country_code = False

                # Include country names?
                if get_yes_or_no("? Include country names ('United Kingdom'): "):
                    include_country_name = True
                    download_file("https://raw.githubusercontent.com/annexare/Countries/main/dist/countries.min.json", "countries.min.json")
                    if os.path.exists("countries.min.json"):
                        with open("countries.min.json", 'r') as f2:
                            country_names = json.load(f2)
                else:
                    include_country_name = False

                # Include alternative place names?
                if get_yes_or_no("? Include alternative place names: "):
                    include_altnames = True
                else:
                    include_altnames = False

                # Include states?
                if get_yes_or_no("? Include states: "):
                    include_state = True
                    # Choose countries to add states to
                    country_list_for_states = input("? Include states for which countries. List country codes separated by a comma. Leave blank for all countries: ")
                    # Use abbreviated US state names?
                    if 'us' in country_list_for_states.lower() or country_list_for_states == '':
                        abbreviate_us_states = get_yes_or_no("? Use abbreviated US state names ('CA' instead of 'California'): ")
                    # Check reference data
                    if disableReference == False:
                        if not ref_data:
                            download_reference_file()
                        # Append only required countries to lookup table
                        ref_data_states = {}
                        for item in ref_data:
                            if item['country'].lower() in country_list_for_states.lower().split(',') or country_list_for_states == '':
                                lat = item['lat']
                                lng = item['lng']
                                name = item['name']
                                ref_data_states[(lat, lng, name)] = item
                else:
                    include_state = False
                    country_list_for_states = None

                # Include counties?
                if get_yes_or_no("? Include counties: "):
                    include_county = True
                    # Choose countries to add counties to
                    country_list_for_counties = input("? Include counties for which countries. List country codes separated by a comma. Leave blank for all countries: ")
                    # Check reference data
                    if disableReference == False:
                        if not ref_data:
                            download_reference_file()
                        # Append only required countries to lookup table
                        ref_data_counties = {}
                        for item in ref_data:
                            if item['country'].lower() in country_list_for_counties.lower().split(',') or country_list_for_counties == '':
                                lat = item['lat']
                                lng = item['lng']
                                name = item['name']
                                ref_data_counties[(lat, lng, name)] = item
                else:
                    include_county = False
                    country_list_for_counties = None

                # Include states only for duplicate place names?
                if (include_state == False):
                    if get_yes_or_no("? Include states only for duplicate place names: "):
                        include_state_for_dupe = True
                    else:
                        include_state_for_dupe = False
                else:
                    include_state_for_dupe = False

                # Include counties only for duplicate place names?
                if (include_county == False):
                    if get_yes_or_no("? Include counties only for duplicate place names: "):
                        include_county_for_dupe = True
                    else:
                        include_county_for_dupe = False
                else:
                    include_county_for_dupe = False
                
                # Choose countries to add dupe states/counties to
                if (include_state_for_dupe == True or include_county_for_dupe == True):
                    country_list_for_dupes = input("? Include states and/or counties for duplicate place names for which countries. List country codes separated by a comma. Leave blank for all countries: ")
                    if 'us' in country_list_for_dupes.lower() or country_list_for_dupes == '':
                        abbreviate_us_states = get_yes_or_no("? Use abbreviated US state names ('CA' instead of 'California'): ")
                    list_country_place,ref_data_states,ref_data_counties = create_ref_data_for_dupes(file,country_list_for_dupes)

                # Include timezones?
                if get_yes_or_no("? Include timezones: "):
                    include_timezone = True
                else:
                    include_timezone = False

                # Include populations?
                if get_yes_or_no("? Include populations: "):
                    include_population = True
                else:
                    include_population = False

                # Include altitudes?
                if get_yes_or_no("? Include altitudes: "):
                    include_altitude = True
                else:
                    include_altitude = False

            # Get start time
            start_time = time.time()

            # Log
            logging.info(f"Selected options: include_country_code: {include_country_code}, include_country_name: {include_country_name}, include_state: {include_state}, include_county: {include_county}, include_altnames: {include_altnames}, include_timezone: {include_timezone}, include_population: {include_population}, include_altitude: {include_altitude}")
            logging.info(f"Time started: {start_time}")

            # Process each item
            print("> Processing data...")
            for line in file:
                # Reset vars
                state = None
                county = None
                is_dupe = None
                include_state_once = None
                include_county_once = None

                # Split data on each line at tab space
                line_data = line.decode('utf-8').strip().split('\t')

                # Include country names if true
                if (include_country_name == True):
                    country_name = country_names[line_data[8]]['name']
                else:
                    country_name = ''

                # Duplicate place names?
                if (include_state_for_dupe == True or include_county_for_dupe == True):
                    # If the current item country is in the listed countries
                    if line_data[8].lower() in country_list_for_dupes.lower().split(',') or country_list_for_dupes == '':
                        # Find duplicates
                        dupe_count = 0
                        value_to_check = (line_data[8], line_data[1])
                        dupe_count = list_country_place.count(value_to_check)
                        if (dupe_count > 1):
                            is_dupe = True
                        
                # Includes states for duplicate place names?
                if (include_state_for_dupe == True):
                    if (is_dupe == True):
                        include_state_once = True

                # Include states?
                if (include_state == True or include_state_once == True):
                    # Set country list mode
                    if (include_state == True):
                        country_list = country_list_for_states
                    elif (include_state_once == True):
                        country_list = country_list_for_dupes

                    # If the current item country is in the listed countries
                    if line_data[8].lower() in country_list.lower().split(',') or country_list == '':
                        if disableReference == False:
                            # Search ref_data_states lookup table
                            search_lat = line_data[4]
                            search_lng = line_data[5]
                            search_name = line_data[1]
                            search_key = (search_lat, search_lng, search_name)
                            matching_item = ref_data_states.get(search_key, None)
                        else:
                            matching_item = None

                        # If no matches in reference data found, query the api
                        if matching_item:
                            state = matching_item['state']
                        else:
                            logging.info(f"Missing item {line_data[0]} {line_data[1]} {line_data[4]} {line_data[5]}")
                            state = lookUpGeo(line_data[4],line_data[5],'state')

                        # Abbreviate US states
                        if (line_data[8] == 'US'):
                            if (abbreviate_us_states):
                                state = state_abbreviations[state]

                # Includes counties for duplicate place names?
                if (include_county_for_dupe == True):
                    if (is_dupe == True):
                        include_county_once = True

                # Include counties?
                if (include_county == True or include_county_once == True):
                    # Set country list mode
                    if (include_county == True):
                        country_list = country_list_for_counties
                    elif (include_county_once == True):
                        country_list = country_list_for_dupes
                    
                    # If the current item country is in the listed countries
                    if line_data[8].lower() in country_list.lower().split(',') or country_list == '':
                        if disableReference == False:
                            # Search ref_data_counties lookup table
                            search_lat = line_data[4]
                            search_lng = line_data[5]
                            search_name = line_data[1]
                            search_key = (search_lat, search_lng, search_name)
                            matching_item = ref_data_counties.get(search_key, None)
                        else:
                            matching_item = None

                        # If no matches in reference data found, query the api
                        if matching_item:
                            county = matching_item['county']
                        else:
                            logging.info(f"Missing item {line_data[0]} {line_data[1]} {line_data[4]} {line_data[5]}")
                            county = lookUpGeo(line_data[4],line_data[5],'county')

                if state is not None and county is not None:
                    # Create a JSON object for each line with state
                    item = {
                        'country': line_data[8],
                        'country_name': country_name,
                        'state': state,
                        'county': county,
                        'name': line_data[1],
                        'altnames': line_data[3],
                        'lat': line_data[4],
                        'lng': line_data[5],
                        'timezone': line_data[17],
                        'population': line_data[14],
                        'altitude': line_data[16],
                    }
                elif state is not None and county is None:
                    # Create a JSON object for each line with state
                    item = {
                        'country': line_data[8],
                        'country_name': country_name,
                        'state': state,
                        'name': line_data[1],
                        'altnames': line_data[3],
                        'lat': line_data[4],
                        'lng': line_data[5],
                        'timezone': line_data[17],
                        'population': line_data[14],
                        'altitude': line_data[16],
                    }
                elif state is None and county is not None:
                    # Create a JSON object for each line with county
                    item = {
                        'country': line_data[8],
                        'country_name': country_name,
                        'county': county,
                        'name': line_data[1],
                        'altnames': line_data[3],
                        'lat': line_data[4],
                        'lng': line_data[5],
                        'timezone': line_data[17],
                        'population': line_data[14],
                        'altitude': line_data[16],
                    }
                else:
                    # Create a JSON object for each line not including states or county
                    item = {
                        'country': line_data[8],
                        'country_name': country_name,
                        'name': line_data[1],
                        'altnames': line_data[3],
                        'lat': line_data[4],
                        'lng': line_data[5],
                        'timezone': line_data[17],
                        'population': line_data[14],
                        'altitude': line_data[16],
                    }

                # Remove key(s) if false
                if (include_country_code == False):
                    if 'country' in item:
                        del item['country']
                if (include_country_name == False):
                    if 'country_name' in item:
                        del item['country_name']
                if (include_altnames == False):
                    if 'altnames' in item:
                        del item['altnames']
                if (include_timezone == False):
                    if 'timezone' in item:
                        del item['timezone']
                if (include_population == False):
                    if 'population' in item:
                        del item['population']
                if (include_altitude == False):
                    if 'altitude' in item:
                        del item['altitude']

                json_data.append(item)

                count += 1
                print(f"> {count}/{totalItems}", end='\r')
            
            print(f"> Processed {totalItems} items")
            print(f"> Geocode Queries: {lookup_count}")
            
            # Get end time
            end_time = time.time()

            # Time elapsed
            elapsed_time = round(end_time - start_time, 2)
            print(f'> Elapsed time: {elapsed_time}s')

            # Log
            logging.info(f'Processed {totalItems} items')
            logging.info(f'Time finished: {end_time}')
            logging.info(f'Elapsed time: {elapsed_time}')

    return json_data

# Main function
def main():
    # If preset argument is used, set preset defaults, otherwise, prompt user
    if (preset == 1):
        population_threshold = '1000'
        filename = 'world_cities'
        filetype = 'csv'
    elif (preset == 2):
        population_threshold = '1000'
        filename = 'world_cities_(including_US_states)'
        filetype = 'csv'
    elif (preset == 3):
        population_threshold = '1000'
        filename = 'world_cities_(including_states_and_counties_for_duplicate_names)'
        filetype = 'csv'
    elif (preset == 4):
        population_threshold = '1000'
        filename = 'world_cities_(including_all_states_and_counties)'
        filetype = 'csv'
    else:
        # Prompt the user for cities version
        population_threshold = get_pop_threshold("? Population threshold. (Only include places with greater than '1000', '5000', or '15000' in population): ")

        # Prompt the user for an output filename
        filename = input("? Enter output filename: ")
        if (filename == ''):
            filename = 'cities'
            print(f"> Using default filename {filename}")

        # Prompt user for file out type
        filetype = get_format("? Enter file format ('json' or 'csv'): ")

    # Download the zip file
    zip_file_path = f"cities{population_threshold}.zip"
    download_file(f"https://download.geonames.org/export/dump/cities{population_threshold}.zip", zip_file_path)

    # Strip file extension if provided
    filename = filename.rsplit( '.', 1 )[ 0 ]

    # Extract and process the text file
    text_file_name = f'cities{population_threshold}.txt'
    print(f"> Extracting {text_file_name}...")
    json_data = process_text_file(zip_file_path, text_file_name)

    # Save the output data
    output_filename = filename + '.' + filetype
    print(f"> Saving to {output_filename}")

    try:
        if (filetype == 'json'):
            with open(output_filename, 'w', encoding='utf-8') as outfile:
                json.dump(json_data, outfile, ensure_ascii=False, indent=2)
                logging.info(f'Saving file: {outfile}')
        elif (filetype == 'csv'):
            # Specify the desired order of keys
            custom_order = ['country', 'country_name', 'state', 'county', 'name', 'altnames', 'lat', 'lng', 'timezone', 'population', 'altitude']
            # Remove unused keys
            if (include_country_code == False):
                    custom_order.remove('country')
            if (include_country_name == False):
                    custom_order.remove('country_name')
            if (include_state == False and include_state_for_dupe == False):
                    custom_order.remove('state')
            if (include_county == False and include_county_for_dupe == False):
                    custom_order.remove('county')
            if (include_altnames == False):
                    custom_order.remove('altnames')
            if (include_timezone == False):
                    custom_order.remove('timezone')
            if (include_population == False):
                    custom_order.remove('population')
            if (include_altitude == False):
                    custom_order.remove('altitude')

            # Write the JSON data to a CSV file with custom key order
            with open(output_filename, 'w', newline='') as outfile:
                csv_writer = csv.writer(outfile)

                # Write the header row using the custom order
                csv_writer.writerow(custom_order)

                # Write the data rows with custom key order
                for item in json_data:
                    row_data = [item.get(key, '') for key in custom_order]
                    csv_writer.writerow(row_data)
                logging.info(f"Saving file: {output_filename}")
    except IOError as e:
        logging.error(f"Failed to save {output_filename}. {e}")

# Detect CTRL+C
def signal_handler(sig, frame):
    logging.error("Script was killed by user.")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
