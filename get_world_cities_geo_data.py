#!/usr/bin/env python

# GetWorldCitiesGeoData
#
version = "2.1.0"
#
# Author: github.com/joelacus
#
# Repo: github.com/joelacus/world-cities
#
# Generate a json/csv file of all the cities in the world with various extra data.

# ===== Import Libraries =====

import argparse
import csv
import json
import logging
import os
import signal
import sys
import time
import zipfile
import threading
import time


# Check if extra required libraries are installed
def check_libraries(libraries):
    missing_libraries = []

    for library in libraries:
        try:
            __import__(library)
        except ImportError:
            missing_libraries.append(library)

    if missing_libraries:
        print("Error: The following required libraries are not installed:")
        for lib in missing_libraries:
            print(f" - {lib}")
        print("Please install the missing libraries with the following command:")
        print(f"pip install {' '.join(missing_libraries)}")
        sys.exit(1)


check_libraries(["enlighten", "requests", "pickledb"])

# Continue importing libraries
import enlighten
import requests
from typing import List, Optional
from requests.exceptions import RequestException, HTTPError
import pickle


# ===== Argument Parser =====

parser = argparse.ArgumentParser(
    prog="python get_world_cities.py",
    description=f"Generate a custom csv/json file of all the cities in the world.\n\nVersion: {version}\nAuthor: github.com/joelacus",
)

# Arguments
parser.add_argument(
    "-v", "--version", action="store_true", help="Show the version number."
)
parser.add_argument(
    "-c", "--convert", help="Convert file.csv to file.json, or vice versa."
)
parser.add_argument(
    "-r", "--resume", action="store_true", help="Resume from a save file."
)
parser.add_argument(
    "-l",
    "--log",
    action="store_true",
    help="Save a log file in the same directory as the script.",
)
parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Optional. Specify an output filename instead of being prompted for one.",
)
parser.add_argument(
    "-t",
    "--threshold",
    type=int,
    help="Optional. Population threshold. Specify a dataset with places/cities of a population greater than 500/1000/5000/15000, otherwise you will be prompted.",
)
parser.add_argument(
    "-dr",
    "--disable_reference",
    action="store_true",
    help="Don't use a preloaded reference file to save time, but instead query geocode.maps.co api for every request to get state and/or county data. This will take a very long time (not recommended).",
)
parser.add_argument(
    "-drd",
    "--disable_reference_download",
    action="store_true",
    help="Don't download the reference file if it already exists in the directory. It will be downloaded if it does not exist.",
)
parser.add_argument(
    "-p1",
    "--preset1",
    action="store_true",
    help="Pre-select options to save a CSV file with country, place name, latitude, longitude.",
)
parser.add_argument(
    "-p2",
    "--preset2",
    action="store_true",
    help="Pre-select options to save a CSV file with country, US states, place name, latitude, longitude.",
)
parser.add_argument(
    "-p3",
    "--preset3",
    action="store_true",
    help="Pre-select options to save a CSV file with country, states for duplicated place names, counties for duplicated place names, place name, latitude, longitude.",
)
parser.add_argument(
    "-p0",
    "--preset0",
    action="store_true",
    help="Pre-select options to save a CSV file with country, state, county, name, latitude, longitude. (Reference File)",
)


# Parse the command-line arguments
args = parser.parse_args()

resume = False
log = False
disableReference = False
disableReferenceDownload = False
preset = None
threshold = None
threshold_prompt_fallback = False
output = None


# Arg - Convert
def get_custom_csv_header_order():
    custom_order = [
        "continent",
        "country",
        "country_name",
        "state",
        "county",
        "geonameid",
        "name",
        "altnames",
        "lat",
        "lng",
        "timezone",
        "population",
        "altitude",
        "capital",
        "currency_code",
        "currency_name",
        "phone",
        "languages",
        "neighbours",
    ]
    return custom_order


if args.convert:
    filename = os.path.splitext(args.convert)[0]
    ext = os.path.splitext(args.convert)[1]

    if ext == ".csv":
        # Read the CSV file
        with open(args.convert, "r") as csv_file:
            csv_reader = csv.DictReader(csv_file)

            # Convert to JSON
            data = []
            for row in csv_reader:
                data.append(row)

        # Write JSON data to a file
        with open(f"{filename}.json", "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2)

    if ext == ".json":
        # Custom key order
        custom_order = get_custom_csv_header_order()

        # Load the JSON data from the input file
        with open(args.convert, "r") as json_file:
            custom_dataset_json = json.load(json_file)

        # Open the CSV file for writing
        with open(f"{filename}.csv", "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)

            # Write the header row using the custom order, but only include existing keys
            existing_keys = [
                key
                for key in custom_order
                if any(key in item for item in custom_dataset_json)
            ]
            csv_writer.writerow(existing_keys)

            # Write the data rows with custom key order, only including existing keys
            for item in custom_dataset_json:
                row_data = [item.get(key, "") for key in existing_keys]
                csv_writer.writerow(row_data)
    sys.exit(0)

# Arg - Version
if args.version:
    print(f"GetWorldCities {version}")
    sys.exit(0)

# Arg - Resume
if args.resume:
    resume = True

# Arg - Log
if args.log:
    log = True

# Arg - Disable Reference File
if args.disable_reference:
    disableReference = True

# Arg - Disable Reference File Download
if args.disable_reference_download:
    disableReferenceDownload = True

# Arg - Preset
if args.preset0:
    preset = 0
if args.preset1:
    preset = 1
if args.preset2:
    preset = 2
if args.preset3:
    preset = 3

# Arg - Population Threshold
if args.threshold in [500, 1000, 5000, 15000]:
    threshold = args.threshold
else:
    threshold = 1000
    threshold_prompt_fallback = True

# Arg - Output filename
if args.output is not None:
    output = args.output


# Logging Config
if log:
    logging.basicConfig(
        filename="get_world_cities.log",
        encoding="utf-8",
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


# ===== Spinner =====

spinner_chars = ["|", "/", "-", "\\"]
spinner_running = False
spinner_thread = None
spinner_text = ""


def spinner():
    while spinner_running:
        for char in spinner_chars:
            sys.stdout.write(f"\r{char} {spinner_text}...")
            sys.stdout.flush()
            time.sleep(0.1)


def start_spinner(text):
    global spinner_running, spinner_thread, spinner_text
    spinner_running = True
    spinner_text = text
    spinner_thread = threading.Thread(target=spinner)
    spinner_thread.start()


def stop_spinner(end_text=""):
    global spinner_running
    spinner_running = False
    spinner_thread.join()
    sys.stdout.write(f"\r✔ {spinner_text}... {end_text}\n")
    sys.stdout.flush()


# ===== Define US States =====

# Define a dictionary to map full state names to abbreviations for all US states.

state_abbreviations = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
}


# ===== Geocode API =====

# Check Geocode API Key
geocode_api_key = None


def checkGeocodeKey():
    global geocode_api_key
    if geocode_api_key is not None:
        return geocode_api_key
    else:
        if os.path.exists("geocode_maps_api_key.txt"):
            try:
                with open("geocode_maps_api_key.txt", "r") as geocode_api_key_file:
                    geocode_api_key = geocode_api_key_file.readline().strip()
            except Exception as e:
                logging.error(f"Could not read {geocode_api_key_file} into object. {e}")
                geocode_api_key = prompt_geocode_api_key()
        else:
            geocode_api_key = prompt_geocode_api_key()
    return geocode_api_key


# Prompt for Geocode API key if required
def prompt_geocode_api_key():
    print("> Geocode API Key is required.")
    geocode_api_key = input("? Enter Key: ")
    if get_yes_or_no("? Save the key in the current directory to save you from entering it next time?: "):
        with open("geocode_maps_api_key.txt", "w") as file:
            file.write(geocode_api_key)
    return geocode_api_key


# ===== Download Functions =====


# File Downloader
def download_file(url, filename):
    start_spinner(f"Downloading {filename}")
    try:
        response = requests.get(url)
        try:
            with open(filename, "wb") as file:
                file.write(response.content)
                stop_spinner("done")
            logging.info(f"Downloaded {url} to {filename}.")
        except IOError as e:
            logging.error(f"Could not save {filename}. {e}. Abort!")
            sys.exit(0)
    except requests.exceptions.RequestException as e:
        logging.error(f"Download failed from {url}. {e}. Abort!")
        sys.exit(0)


# File checker
def file_check(url, filename):
    # Check if the file exists
    if os.path.exists(filename):
        # Get the last modified time of the file
        last_modified_time = os.path.getmtime(filename)
        # Get the current time
        current_time = time.time()
        # Calculate the age of the file in seconds (1 day = 86400 seconds)
        file_age = current_time - last_modified_time

        if file_age > 86400:  # 86400 seconds in a day
            print(f"> {filename} is older than a day. Redownloading...")
            download_file(url, filename)
        else:
            print(f"> Found recent {filename} file. Skipping redownload.")
    else:
        print(f"> {filename} does not exist. Downloading...")
        download_file(url, filename)


# Download Reference File (this preloads state and county data which would otherwise take a long time to get from geocode.maps.co api)
global ref_data
ref_data = None


def download_reference_file():
    ref_file = "world_cities_(including_all_states_and_counties).csv"
    if disableReferenceDownload == False:
        file_check(
            "https://raw.githubusercontent.com/joelacus/world-cities/main/world_cities_(including_all_states_and_counties).csv",
            "world_cities_(including_all_states_and_counties).csv",
        )
    if os.path.exists(ref_file):
        try:
            with open(ref_file, "r", encoding="utf-8") as csv_file:
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
        file_check(
            "https://raw.githubusercontent.com/joelacus/world-cities/main/world_cities_(including_all_states_and_counties).csv",
            "world_cities_(including_all_states_and_counties).csv",
        )
        download_reference_file()


# ===== Cities Dataset =====


# Download Cities Dataset
def download_cities_dataset(population_threshold):
    global cities_dataset
    global total_items_in_cities_dataset

    filename_txt = f"cities{population_threshold}.txt"
    filename_zip = f"cities{population_threshold}.zip"
    url = f"https://download.geonames.org/export/dump/cities{population_threshold}.zip"

    file_check(url, filename_zip)

    # Extract cities dataset zip
    start_spinner(f"Reading: {filename_txt} from {filename_zip}")
    if os.path.exists(filename_zip):
        with zipfile.ZipFile(filename_zip, "r") as zip_ref:
            with zip_ref.open(filename_txt) as f:
                cities_dataset = f.readlines()
                total_items_in_cities_dataset = sum(1 for _ in cities_dataset)
                stop_spinner("done")


# Combine Cities Dataset
def combine_cities_dataset():
    print("\n> Adding cities to combined dataset...")

    # Progress bar
    totalItems = sum(1 for _ in cities_dataset)
    manager = enlighten.get_manager()
    progress_bar = manager.counter(total=totalItems, desc="Adding", unit="city")

    # Add cities data to combined dataset
    for line in cities_dataset:
        fields = line.decode("utf-8").strip().split("\t")

        # Create an item for the town/city
        combined_dataset[fields[0]] = {
            "geonameid": int(fields[0]),
            "name": fields[1],
            "asciiname": fields[2],
            "alternatenames": {},  # fields[3].split(',') if fields[3] else [],
            "latitude": float(fields[4]),
            "longitude": float(fields[5]),
            "feature_class": fields[6],
            "feature_code": fields[7],
            "country_code": fields[8],
            "cc2": fields[9],
            "admin1_code": fields[10],
            "admin2_code": fields[11],
            "admin3_code": fields[12],
            "admin4_code": fields[13],
            "population": int(fields[14]) if fields[14] else "",
            "elevation": int(fields[15]) if fields[15] else "",
            "dem": float(fields[16]) if fields[16] else None,
            "timezone": fields[17],
            "modification_date": fields[18],
        }

        progress_bar.update()
    progress_bar.close()
    manager.stop()
    print("\n")


# ===== Country Info Dataset =====


# Download Country Info Dataset
def download_country_info_dataset():
    global countryInfoDataset
    url = "https://download.geonames.org/export/dump/countryInfo.txt"
    filename = "countryInfo.txt"

    file_check(url, filename)

    if os.path.exists(filename):
        with open(filename, "r") as file:
            countryInfoDataset = []
            start_reading = False
            for line in file:
                if line.startswith("#ISO"):
                    start_reading = True
                    continue
                if start_reading:
                    countryInfoDataset.append(line.strip())


# Combine Country Info Dataset
def combine_country_info_dataset():
    print("> Adding country info to combined dataset...")

    # Progress bar
    totalItems = sum(1 for _ in countryInfoDataset)
    manager = enlighten.get_manager()
    progress_bar = manager.counter(total=totalItems, desc="Adding", unit="name")

    # Add alt names to combined dataset
    for line in countryInfoDataset:
        fields = line.strip().split("\t")

        # if len(fields) < 17:
        # progress_bar.update()
        # continue

        iso = fields[0]
        # iso3 = fields[1]
        # isoNumeric = fields[2]
        # fips = fields[3]
        country_name = fields[4]
        capital = fields[5]
        area = fields[6]
        # population = fields[7]
        continent = fields[8]
        # tld = fields[9]
        currencyCode = fields[10]
        currencyName = fields[11]
        phone = fields[12]
        # postalCodeFormat = fields[13]
        # postalCodeRegex = fields[14]
        languages = fields[15]
        geonameid = fields[16]
        neighbours = fields[17] if len(fields) > 17 else ""

        # Append alt name
        for geonameid, value in combined_dataset.items():
            country_code = combined_dataset[geonameid]["country_code"]
            if country_code == iso:
                combined_dataset[geonameid]["country_name"] = country_name
                combined_dataset[geonameid]["capital"] = capital
                combined_dataset[geonameid]["area"] = area
                combined_dataset[geonameid]["continent"] = continent
                combined_dataset[geonameid]["currency_code"] = currencyCode
                combined_dataset[geonameid]["currency_name"] = currencyName
                combined_dataset[geonameid]["phone"] = phone
                combined_dataset[geonameid]["languages"] = languages
                combined_dataset[geonameid]["neighbours"] = neighbours

        progress_bar.update()
    progress_bar.close()
    manager.stop()
    print("\n")


# ===== Alternative Place Names Dataset =====


# Download Alternative Names Dataset
def download_alt_names_dataset():
    global alternative_names_dataset
    url = "https://download.geonames.org/export/dump/alternateNamesV2.zip"
    filename_zip = "alternateNamesV2.zip"
    filename_txt = "alternateNamesV2.txt"

    file_check(url, filename_zip)

    if os.path.exists(filename_zip):
        start_spinner(f"Reading {filename_txt} from {filename_zip}")
        with zipfile.ZipFile(filename_zip, "r") as zip_ref:
            with zip_ref.open(filename_txt) as f:
                alternative_names_dataset = f.readlines()
                stop_spinner("done")


# Combine Alternative Names Dataset
def combine_altname_dataset(alternative_names_dataset):
    print("> Adding alternative names to combined dataset...")

    # Progress bar
    totalItems = sum(1 for _ in alternative_names_dataset)
    manager = enlighten.get_manager()
    progress_bar = manager.counter(total=totalItems, desc="Adding", unit="name")

    # Add alt names to combined dataset
    for line in alternative_names_dataset:
        fields = line.decode("utf-8").strip().split("\t")

        if len(fields) < 4:
            progress_bar.update()
            continue

        geonameid = fields[1]
        isolanguage = fields[2]
        alternate_name = fields[3]

        if isolanguage == "":
            isolanguage = "?"

        # Append alt name
        if isolanguage not in ["link", "wkdt", "unlc", "post", "iata"]:
            if geonameid in combined_dataset:
                if isolanguage not in combined_dataset[geonameid]["alternatenames"]:
                    combined_dataset[geonameid]["alternatenames"][isolanguage] = []
                combined_dataset[geonameid]["alternatenames"][isolanguage].append(
                    alternate_name
                )

        progress_bar.update()
    progress_bar.close()
    manager.stop()
    print("\n")


# ===== GeoCode API =====

if not "geocode_lookup_count" in globals():
    geocode_lookup_count = 0
county = ""
state = ""


def geocode_lookup(lat, lng):
    global geocode_lookup_count
    max_retries = 5

    # Get Geocode API Key
    geocode_api_key = checkGeocodeKey()

    # Construct the geocoding URL
    geocode_url = (f"https://geocode.maps.co/reverse?lat={lat}&lon={lng}&api_key={geocode_api_key}")

    time.sleep(1)

    for attempt in range(max_retries + 1):
        try:
            # Implement rate limiting with exponential backoff
            if attempt > 0:
                wait_time = 2**attempt  # Exponential backoff
                # logging.info(f"> Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

            # Perform the request with a timeout
            response = requests.get(geocode_url, timeout=10)

            # Handle specific HTTP error codes
            if response.status_code == 429:
                print("! Rate limit exceeded. Saving resume file and stopping...")
                logging.warning("Rate limit exceeded. Saving resume file and stopping...")
                saveAndStop()
                continue

            if response.status_code == 503:
                print("! Service unavailable. Retrying...")
                logging.error("Service unavailable. Retrying...")
                continue

            # Raise an exception for other HTTP errors
            response.raise_for_status()

            # Parse the JSON response
            geocode_data = response.json()
            address = geocode_data.get("address", {})

            # Extract state and county with fallback
            state = address.get("state", "")
            county = address.get("county", "")

            geocode_lookup_count += 1

            # logging.info(f"Geocode lookup successful: State={state}, County={county}")
            return [state, county]

        except RequestException as e:
            logging.error(f"Request error for coordinates {lat},{lng}: {e}")

            # Different handling for different types of request exceptions
            if isinstance(e, HTTPError):
                if e.response.status_code == 429:
                    logging.warning("Rate limit exceeded. Backing off...")
                    print("> Rate limit exceeded. Backing off...")
                    saveAndStop()
                elif e.response.status_code == 503:
                    logging.error("Service unavailable. Retrying...")

            # If it's the last attempt, re-raise the exception
            if attempt == max_retries:
                logging.error(f"Failed to retrieve geocode after {max_retries} attempts")
                saveAndStop()

#===== geo.fcc.gov API Lookup =====

if not "geo_fcc_lookup_count" in globals():
    geo_fcc_lookup_count = 0

def geo_fcc_lookup(lat, lng):
    global geo_fcc_lookup_count
    max_retries = 5

    # Construct the geocoding URL
    geo_fcc_url = (f"https://geo.fcc.gov/api/census/area?lat={lat}&lon={lng}&censusYear=2020&format=json")

    time.sleep(1)

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = 2**attempt
                time.sleep(wait_time)

            # Perform the request with a timeout
            response = requests.get(geo_fcc_url, timeout=10)

            if response.status_code == 503:
                print("! Service unavailable. Retrying...")
                logging.error("Service unavailable. Retrying...")
                continue

            # Raise an exception for other HTTP errors
            response.raise_for_status()

            # Parse the JSON response and extract the county name
            geocode_data = response.json()
            county = geocode_data.get("results", [{}])[0].get("county_name", "")

            geo_fcc_lookup_count += 1

            return county

        except RequestException as e:
            logging.error(f"Request error for coordinates {lat},{lng}: {e}")

            # Different handling for different types of request exceptions
            if isinstance(e, HTTPError):
                if e.response.status_code == 503:
                    logging.error("Service unavailable. Retrying...")

            # If it's the last attempt, re-raise the exception
            if attempt == max_retries:
                logging.error(f"Failed to retrieve geocode after {max_retries} attempts")
                saveAndStop()


# Count duplicate items (country_code, name)
def count_duplicate_items():
    count_items = {}
    for geonameid, value in combined_dataset.items():
        key = (value["country_code"], value["name"])
        if key not in count_items:
            count_items[key] = 0
        count_items[key] += 1
    return count_items


# Create a list of geonameids for state geocode lookup
def create_state_geocode_list(state_geocode_list):
    count_items = count_duplicate_items()

    # Append geonameid to list
    for geonameid, value in combined_dataset.items():
        if (
            value["country_code"].lower() in country_list_for_states.lower().split(",")
            or country_list_for_states == ""
        ):
            if include_state_for_dupe == True:
                key = (value["country_code"], value["name"])
                if count_items[key] > 1:
                    state_geocode_list.append(geonameid)
            else:
                state_geocode_list.append(geonameid)
    print(f"> Total number of states to lookup: {len(state_geocode_list)}")
    return state_geocode_list


# Create a list of geonameids for county geocode lookup
def create_county_geocode_list(county_geocode_list):
    count_items = count_duplicate_items()

    # Append geonameid to list
    for geonameid, value in combined_dataset.items():
        if (
            value["country_code"].lower()
            in country_list_for_counties.lower().split(",")
            or country_list_for_counties == ""
        ):
            if include_county_for_dupe == True:
                key = (value["country_code"], value["name"])
                if count_items[key] > 1:
                    county_geocode_list.append(geonameid)
            else:
                county_geocode_list.append(geonameid)
    print(f"> Total number of counties to lookup: {len(county_geocode_list)}")
    return county_geocode_list


# Combine State and County Data
def combine_state_and_county_data(state_geocode_list, county_geocode_list):
    state_and_county_list = list(set(state_geocode_list) | set(county_geocode_list))
    total_items_to_lookup = len(state_and_county_list)

    global geocodeLookupStarted
    geocodeLookupStarted = True

    print(f"> Fetching state and county data for {total_items_to_lookup} cities...\n")

    manager = enlighten.get_manager()
    progress_bar = manager.counter(
        total=total_items_to_lookup, desc="Fetching", unit="city"
    )

    if not "found_resume_target" in locals():
        found_resume_target = False

    if not "current_geonameid" in globals():
        global current_geonameid
        current_geonameid = None

    if not "count_file" in globals():
        global count_file
        count_file = 0

    for geonameid, value in combined_dataset.items():
        if (resume == True) and (not found_resume_target):
            if geonameid != current_geonameid:
                if geonameid in state_and_county_list:
                    progress_bar.update()
                continue
            found_resume_target = True
            print(f"> Skipped to: {geonameid}")

        current_geonameid = geonameid
        if geonameid in state_and_county_list:
            key = (
                combined_dataset[geonameid]["latitude"],
                combined_dataset[geonameid]["longitude"],
            )

            def get_state_and_county_from_geocode():
                [state, county] = geocode_lookup(value["latitude"], value["longitude"])
                print(f"> Fetched state and county from geocode: {key} - {state if state else 'unknown'} - {county if county else 'unknown'}")
                combined_dataset[geonameid]["state"] = state
                combined_dataset[geonameid]["county"] = county

            if reference_dataset.get(key):
                # Force refetch of empty values
                # state = reference_dataset.get(key, {}).get("state")
                # county = reference_dataset.get(key, {}).get("county")
                # if not state and not county:
                # get_state_and_county_from_geocode()
                # else:
                state = reference_dataset.get(key, {}).get("state")
                county = reference_dataset.get(key, {}).get("county")
                if state != "" or county != "": 
                    count_file += 1
                combined_dataset[geonameid]["state"] = state
                combined_dataset[geonameid]["county"] = county
            else:
                get_state_and_county_from_geocode()
            
            # Secondary county name fetcher for US locations
            if (combined_dataset[geonameid]["country_code"] == "US" and combined_dataset[geonameid]["county"] == ""):
                county = geo_fcc_lookup(value["latitude"], value["longitude"])
                print(f"> Fetched county from geo.fcc.gov: {key} - {county if county else 'unknown'}")
                combined_dataset[geonameid]["county"] = county
            
            progress_bar.update()
    progress_bar.close()
    manager.stop()

    print("Fetched From File: ", count_file)
    print("Fetched From Geocode: ", geocode_lookup_count)
    print("Fetched From Geo FCC: ", geo_fcc_lookup_count)
    

    print("Total: ", count_file + geocode_lookup_count + geo_fcc_lookup_count)


# ===== Process Datasets and Generate Custom Dataset =====


# Prompt user, download and combine datasets, and create custom dataset
def process_datasets(population_threshold):
    # Prompt and set variables for which attributes to include in the custom dataset
    set_include_attributes()

    # Get start time
    global start_time
    start_time = time.time()

    # Log
    logging.info(f"Selected options: include_country_code: {include_country_code}, include_country_name: {include_country_name}, include_state: {include_state}, include_county: {include_county}, include_altnames: {include_altnames}, include_timezone: {include_timezone}, include_population: {include_population}, include_altitude: {include_altitude}")
    logging.info(f"Time started: {start_time}")

    # Start
    print("> Processing data...")

    global combined_dataset
    combined_dataset = {}

    # Add cities dataset to combined_dataset
    download_cities_dataset(population_threshold)
    combine_cities_dataset()

    # Add alternative place names dataset to combined_dataset
    if include_altnames == True:
        download_alt_names_dataset()
        combine_altname_dataset(alternative_names_dataset)

    # Add country info dataset to combined_dataset
    if (
        include_country_name == True
        or include_capital == True
        or include_continent == True
        or include_currency_code == True
        or include_currency_name == True
        or include_languages == True
        or include_country_neighbours == True
    ):
        download_country_info_dataset()
        combine_country_info_dataset()

    # Get list of items to add state
    global state_geocode_list
    state_geocode_list = []
    if include_state == True:
        state_geocode_list = create_state_geocode_list(state_geocode_list)

    # Get list of items to add county
    global county_geocode_list
    county_geocode_list = []
    if include_county == True:
        county_geocode_list = create_county_geocode_list(county_geocode_list)

    # Continue to part 2
    return process_datasets_2()


# Split so the resume function can start from here
def process_datasets_2():
    # Combine State and County Data
    combine_state_and_county_data(state_geocode_list, county_geocode_list)

    # Generate required data
    custom_dataset_json = generate_custom_dataset(combined_dataset)

    # print(f"\n> Processed {total_items_in_cities_dataset} items")
    # print(f"> Geocode Queries: {geocode_lookup_count}")

    if resume == False:
        # Get end time
        end_time = time.time()

        # Time elapsed
        elapsed_time = round(end_time - start_time, 2)

        def convert_seconds_with_milliseconds(elapsed_time):
            hours = int(elapsed_time // 3600)
            remaining_seconds = elapsed_time % 3600
            minutes = int(remaining_seconds // 60)
            remaining_seconds %= 60
            seconds = int(remaining_seconds)
            milliseconds = (remaining_seconds - seconds) * 1000
            return hours, minutes, seconds, milliseconds

        hours, minutes, seconds, milliseconds = convert_seconds_with_milliseconds(
            elapsed_time
        )
        print(f"> Elapsed time: {hours} hours, {minutes} minutes, {seconds} seconds, and {milliseconds:.2f} milliseconds.")

        # Log
        logging.info(f"Time finished: {end_time}")
        logging.info(f"Elapsed time: {elapsed_time}")

    logging.info(f"Processed {total_items_in_cities_dataset} items")

    return custom_dataset_json


# ===== Save and Resume =====

resume_filename = "resume_data.dat"


# Save and Stop
def saveAndStop():
    print(f"\n> Stopped at geocodeid: {current_geonameid}")
    start_spinner(f"Saving resume data to {resume_filename}")
    resume_data = [
        {
            "current_geonameid": current_geonameid,
            "filetype": filetype,
            "filename": filename,
            "include_country_code": include_country_code,
            "include_country_name": include_country_name,
            "include_altnames": include_altnames,
            "include_geonameid": include_geonameid,
            "include_state": include_state,
            "include_county": include_county,
            "include_state_for_dupe": include_state_for_dupe,
            "include_county_for_dupe": include_county_for_dupe,
            "include_timezone": include_timezone,
            "include_population": include_population,
            "include_altitude": include_altitude,
            "include_continent": include_continent,
            "include_capital": include_capital,
            "include_currency_code": include_currency_code,
            "include_currency_name": include_currency_name,
            "include_phone": include_phone,
            "include_languages": include_languages,
            "include_country_neighbours": include_country_neighbours,
            "abbreviate_us_states": abbreviate_us_states,
            "country_list_for_states": country_list_for_states,
            "country_list_for_counties": country_list_for_counties,
            "county_geocode_list": county_geocode_list,
            "state_geocode_list": state_geocode_list,
            "total_items_in_cities_dataset": total_items_in_cities_dataset,
            "geocode_lookup_count": geocode_lookup_count,
            "count_file": count_file,
            "reference_dataset": reference_dataset,
            "combined_dataset": combined_dataset,
        }
    ]

    with open(resume_filename, "wb") as handle:
        pickle.dump(resume_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
        stop_spinner("done\n")
        sys.exit(0)


# Resume
def resumeFromSave():
    start_spinner(f"Loading resume file {resume_filename}")
    resume_data = []
    with open(resume_filename, "rb") as file:
        try:
            while True:
                resume_data.extend(pickle.load(file))
                # print(resume_data)
                variables = {key: value for key, value in resume_data[0].items()}
                for key, value in variables.items():
                    globals()[key] = value
                # for key, value in resume_data[0].items():
                # print(key, value)
                stop_spinner("done\n")
                print(f"> Resuming from geocodeid: {current_geonameid}\n")
                # sys.exit(0)
        except EOFError:
            pass


# ===== Generate Custom Dataset =====


def generate_custom_dataset(combined_dataset):
    print("\n> Generating custom dataset...")
    custom_dataset_json = []
    manager = enlighten.get_manager()
    progress_bar = manager.counter(total=len(combined_dataset), desc="Generating", unit="item")

    for geonameid, value in combined_dataset.items():

        # Create JSON object for current line/place
        item = {
            "name": value["name"],
            "lat": value["latitude"],
            "lng": value["longitude"],
        }

        # Include Geonameid
        if include_geonameid == True:
            item["geonameid"] = value["geonameid"]

        # Include Alternative Names
        if include_altnames == True:
            item["altnames"] = value["alternatenames"]

        # Include Timezone?
        if include_timezone == True:
            item["timezone"] = value["timezone"]

        # Include Population?
        if include_population == True:
            item["population"] = value["population"]

        # Include Altitude?
        if include_altitude == True:
            item["altitude"] = value["elevation"]

        # Include Country Code?
        if include_country_code == True:
            item["country"] = value["country_code"]

        # Include Country Names?
        if include_country_name == True:
            item["country_name"] = value["country_name"]

        # Include State
        if include_state == True:
            if geonameid in state_geocode_list:
                item["state"] = value["state"]

        # Include County
        if include_county == True:
            if geonameid in county_geocode_list:
                item["county"] = value["county"] if value["county"] else ""

        # Include Country Capital?
        if include_capital == True:
            item["capital"] = value["capital"]

        # Include Continent?
        if include_continent == True:
            item["continent"] = value["continent"]

        # Include Currency Code?
        if include_currency_code == True:
            item["currency_code"] = value["currency_code"]

        # Include Currency Name?
        if include_currency_name == True:
            item["currency_name"] = value["currency_name"]

        # Include Phone?
        if include_phone == True:
            item["phone"] = value["phone"]

        # Include Languages?
        if include_languages == True:
            item["languages"] = value["languages"]

        # Include Neighbours?
        if include_country_neighbours == True:
            item["neighbours"] = value["neighbours"]

        custom_dataset_json.append(item)
        progress_bar.update()
    progress_bar.close()
    manager.stop()
    return custom_dataset_json


# ===== CLI Prompts =====


# Yes/No prompt
def get_yes_or_no(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response.lower() == "yes" or response.lower() == "y":
            return True
        elif response.lower() == "no" or response.lower() == "n":
            return False
        else:
            print("> Please enter '(y)es' or '(n)o'.")


# Population threshold prompt
def get_population_threshold(prompt):
    while True:
        response = input(prompt).strip()
        if response == "500":
            return "500"
        elif response == "1000":
            return "1000"
        elif response == "5000":
            return "5000"
        elif response == "15000":
            return "15000"
        else:
            print("> Please enter '500', '1000', '5000', or '15000'.")


# Filename prompt
def get_filename(prompt, filetype):
    while True:
        response = input(prompt).strip()
        if response == "":
            print(f"> Invalid filename.")
            continue

        filename = response.rsplit(".", 1)[0] + "." + filetype
        if not os.path.exists(filename):
            return filename
        else:
            print(f"> File '{filename}' already exists.")
            overwrite = get_yes_or_no("? Overwrite?")
            if overwrite == True:
                return filename


# File format prompt
def get_format(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response == "json":
            return "json"
        elif response == "csv":
            return "csv"
        else:
            print("> Please enter 'json' or 'csv'.")


# Prompt and set variables for which attributes to include in the custom dataset
def set_include_attributes():
    # Init vars
    global include_country_code
    include_country_code = False
    global include_country_name
    include_country_name = False
    global include_altnames
    include_altnames = False
    global include_geonameid
    include_geonameid = False
    global include_state
    include_state = False
    global include_county
    include_county = False
    global include_state_for_dupe
    include_state_for_dupe = False
    global include_county_for_dupe
    include_county_for_dupe = False
    global include_timezone
    include_timezone = False
    global include_population
    include_population = False
    global include_altitude
    include_altitude = False
    global include_continent
    include_continent = False
    global include_capital
    include_capital = False
    global include_currency_code
    include_currency_code = False
    global include_currency_name
    include_currency_name = False
    global include_phone
    include_phone = False
    global include_languages
    include_languages = False
    global include_country_neighbours
    include_country_neighbours = False
    global abbreviate_us_states
    abbreviate_us_states = False
    global country_list_for_states
    country_list_for_states = ""
    global country_list_for_counties
    country_list_for_counties = ""
    global reference_dataset
    reference_dataset = {}

    # Reference Dataset
    if disableReference == False:
        print("> Using prefetched reference dataset to optimise fetching State and County data.")
        if not ref_data:
            download_reference_file()
        combined_country_list = list(
            filter(
                bool,
                set(country_list_for_states.lower().split(","))
                | set(country_list_for_counties.lower().split(",")),
            )
        )
        start_spinner(f"Creating reference dataset with countries: {combined_country_list if combined_country_list else '(all)'}")
        # Append only required countries to lookup table
        for item in ref_data:
            if (
                item["country"].lower() in combined_country_list
                or combined_country_list == []
            ):
                lat = float(item["lat"])
                lng = float(item["lng"])
                name = item["name"]
                reference_dataset[(lat, lng)] = item
        stop_spinner("done")
    else:
        print("> Reference dataset will NOT be used. Fetching State and County data will take a long time.")

    # If preset argument is used, set preset defaults, otherwise, prompt user for which data to include
    if preset == 0:
        include_country_code = True
        include_state = True
        ref_data_states = {}
        if ref_data:
            for item in ref_data:
                lat = float(item["lat"])
                lng = float(item["lng"])
                name = item["name"]
                ref_data_states[(lat, lng, name)] = item
        include_county = True
        ref_data_counties = {}
        if ref_data:
            for item in ref_data:
                lat = float(item["lat"])
                lng = float(item["lng"])
                name = item["name"]
                ref_data_counties[(lat, lng, name)] = item
    elif preset == 1:
        include_country_code = True
    elif preset == 2:
        include_country_code = True
        include_state = True
        country_list_for_states = "us"
        ref_data_states = {}
        for item in ref_data:
            if item["country"].lower() in "us":
                lat = float(item["lat"])
                lng = float(item["lng"])
                name = item["name"]
                ref_data_states[(lat, lng, name)] = item
        abbreviate_us_states = True
    elif preset == 3:
        include_country_code = True
        include_state = True
        include_state_for_dupe = True
        include_county = True
        include_county_for_dupe = True
    else:
        # Include country codes?
        if get_yes_or_no("? Include ISO-3166 2-letter country codes ('GB'): "):
            include_country_code = True
        else:
            include_country_code = False

        # Include country names?
        if get_yes_or_no("? Include country names ('United Kingdom'): "):
            include_country_name = True
        else:
            include_country_name = False

        # Include alternative place names?
        if get_yes_or_no("? Include alternative place names: "):
            include_altnames = True
        else:
            include_altnames = False

        # Include geonameid?
        if get_yes_or_no("? Include geonameid: "):
            include_geonameid = True
        else:
            include_geonameid = False

        # Include states?
        if get_yes_or_no("? Include states: "):
            include_state = True
            # Choose countries to add states to
            country_list_for_states = input("? Include states for which countries. List country codes separated by a comma. Leave blank for all countries: ")
            # Use abbreviated US state names?
            if "us" in country_list_for_states.lower() or country_list_for_states == "":
                abbreviate_us_states = get_yes_or_no("? Use abbreviated US state names ('CA' instead of 'California'): ")
        else:
            include_state = False
            country_list_for_states = ""

        # Include states only for duplicate place names?
        if include_state == True:
            if get_yes_or_no("? Include states only for duplicate place names: "):
                include_state_for_dupe = True
            else:
                include_state_for_dupe = False
        else:
            include_state_for_dupe = False

        # Include counties?
        if get_yes_or_no("? Include counties: "):
            include_county = True
            # Choose countries to add counties to
            country_list_for_counties = input("? Include counties for which countries. List country codes separated by a comma. Leave blank for all countries: ")
        else:
            include_county = False
            country_list_for_counties = ""

        # Include counties only for duplicate place names?
        if include_county == True:
            if get_yes_or_no("? Include counties only for duplicate place names: "):
                include_county_for_dupe = True
            else:
                include_county_for_dupe = False
        else:
            include_county_for_dupe = False

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

        # Include continents?
        if get_yes_or_no("? Include continents: "):
            include_continent = True
        else:
            include_continent = False

        # Include capital cities?
        if get_yes_or_no("? Include capital cities: "):
            include_capital = True
        else:
            include_capital = False

        # Include currency codes?
        if get_yes_or_no("? Include currency codes: "):
            include_currency_code = True
        else:
            include_currency_code = False

        # Include currency names?
        if get_yes_or_no("? Include currency names: "):
            include_currency_name = True
        else:
            include_currency_name = False

        # Include phone extensions?
        if get_yes_or_no("? Include phone extensions: "):
            include_phone = True
        else:
            include_phone = False

        # Include languages?
        if get_yes_or_no("? Include languages: "):
            include_languages = True
        else:
            include_languages = False

        # Include country neighbours?
        if get_yes_or_no("? Include country neighbours: "):
            include_country_neighbours = True
        else:
            include_country_neighbours = False


# ===== Title =====
def title():
    os.system("cls" if os.name == "nt" else "clear")
    print(
        r"""
         _    _            _     _ _____ _ _   _           _____           ______      _        
        | |  | |          | |   | /  __ (_) | (_)         |  __ \          |  _  \    | |       
        | |  | | ___  _ __| | __| | /  \/_| |_ _  ___  ___| |  \/ ___  ___ | | | |__ _| |_ __ _ 
        | |/\| |/ _ \| '__| |/ _` | |   | | __| |/ _ \/ __| | __ / _ \/ _ \| | | / _` | __/ _` |
        \  /\  / (_) | |  | | (_| | \__/\ | |_| |  __/\__ \ |_\ \  __/ (_) | |/ / (_| | || (_| |
         \/  \/ \___/|_|  |_|\__,_|\____/_|\__|_|\___||___/\____/\___|\___/|___/ \__,_|\__\__,_|
                                                                                            
                                                                                            
    """
    )


# Main function
def main():
    global filetype
    global filename

    if resume == True:
        resumeFromSave()
    else:
        # If preset argument is used, set preset defaults, otherwise, prompt user
        if preset == 1:
            population_threshold = threshold
            if threshold == 1000:
                filename = "world_cities"
            else:
                filename = f"world_cities_{threshold}"
            filetype = "csv"
        elif preset == 2:
            population_threshold = threshold
            if threshold == 1000:
                filename = "world_cities_(including_US_states)"
            else:
                filename = f"world_cities_{threshold}_(including_US_states)"
            filetype = "csv"
        elif preset == 3:
            population_threshold = threshold
            if threshold == 1000:
                filename = (
                    "world_cities_(including_states_and_counties_for_duplicate_names)"
                )
            else:
                filename = f"world_cities_{threshold}_(including_states_and_counties_for_duplicate_names)"
            filetype = "csv"
        elif preset == 0:
            population_threshold = threshold
            if threshold == 1000:
                filename = "world_cities_(including_all_states_and_counties)"
            else:
                filename = (
                    f"world_cities_{threshold}_(including_all_states_and_counties)"
                )
            filetype = "csv"
        else:
            title()
            # Population threshold prompt
            if threshold_prompt_fallback:
                population_threshold = get_population_threshold("? Population threshold. (Only include places with greater than '500', '1000', '5000', or '15000' in population): ")
            else:
                population_threshold = threshold

            # File format prompt
            filetype = get_format("? Enter file format ('json' or 'csv'): ")

            # Filename prompt
            if output is None:
                filename = get_filename("? Enter output filename: ", filetype)
            else:
                filename = output

            # Strip file extension if provided
            filename = filename.rsplit(".", 1)[0]

    # Get custom dataset
    if resume == True:
        custom_dataset_json = process_datasets_2()
    else:
        custom_dataset_json = process_datasets(population_threshold)

    # Save the output data
    output_filename = filename + "." + filetype

    try:
        if filetype == "json":
            start_spinner(f"Saving to {output_filename}")
            with open(output_filename, "w", encoding="utf-8") as outfile:
                json.dump(custom_dataset_json, outfile, ensure_ascii=False, indent=2)
                logging.info(f"Saving file: {outfile}")
                stop_spinner("done\n")
        elif filetype == "csv":
            # Custom key order
            custom_order = get_custom_csv_header_order()
            # Write the JSON data to a CSV file with custom key order
            start_spinner(f"Saving to {output_filename}")
            with open(output_filename, "w", newline="") as outfile:
                csv_writer = csv.writer(outfile)

                # Write the header row using the custom order, but only include existing keys
                existing_keys = [
                    key
                    for key in custom_order
                    if any(key in item for item in custom_dataset_json)
                ]
                csv_writer.writerow(existing_keys)

                # Write the data rows with custom key order, only including existing keys
                for item in custom_dataset_json:
                    row_data = [item.get(key, "") for key in existing_keys]
                    csv_writer.writerow(row_data)

                logging.info(f"Saving file: {output_filename}")
            stop_spinner("done\n")
    except IOError as e:
        logging.error(f"Failed to save {output_filename}. {e}")
        stop_spinner("failed")


# Detect CTRL+C
def signal_handler(sig, frame):
    logging.error("\n! Script was killed by user.")
    if (
        ("include_state" in globals())
        and ("include_county" in globals())
        and ("geocodeLookupStarted" in globals())
    ):
        if ((include_state == True) or (include_county == True)) and (
            geocodeLookupStarted == True
        ):
            saveAndStop()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
