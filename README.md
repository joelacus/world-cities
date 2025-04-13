# World Cities Geolocation Data

Geolocation data for all of the cities in the world as json/csv. [See Examples](#examples).

`world_cities` (More precise. Villages, towns, and cities of 1000 or more in population. Bigger file size)<br>
`world_cities_5000` (Average. Towns and cities of 5000 or more in population)<br>
`world_cities_15000` (Least precise. Large towns, and cities of 15000 or more in population. Smaller file size)

You can generate your own custom list with extra data with the python script.

_NPM install planned._

## Custom Lists

To generate your own list, run `python get_world_cities_geo_data.py` and follow the CLI prompts.

You can choose whether you want to include cities/places with a population greater than '500', '1000', '5000', or '15000'.

Basic data:

-   Place name
-   Latitude
-   Longitude

Optional additional data:

-   ISO-3166 2-letter country code
-   Full country name
-   Geonameid
-   State
-   County
-   Alternative names
-   Timezone
-   Population
-   Altitude
-   Continent
-   Capital City
-   Currency Code
-   Currency Name
-   Phone Extension
-   Spoken Languages
-   Country Neighbours


A [free Geocoding API key](https://geocode.maps.co/join/) is now required to fetch 'state' and 'county' data.

## Examples

world_cities.json

```
[
  {
    "country": "GB",
    "name": "London",
    "lat": "51.50853",
    "lng": "-0.12574"
  },
  ...
]
```
<br>

world_cities.csv

```
country,name,lat,lng
GB,London,51.50853,-0.12574
...
```

<br>
world_cities_(including_US_states).json

```
[
  {
    "country": "US",
    "state": "NY",
    "name": "New York City",
    "lat": "40.71427",
    "lng": "-74.00597"
  },
  ...
]
```
<br>

world_cities_(including_US_states).csv

```
country,state,name,lat,lng
US,NY,New York City,40.71427,-74.00597
...
```
<br>

custom json file with all data points:

```
{
    "name": "London",
    "lat": 51.50853,
    "lng": -0.12574,
    "geonameid": 2643743,
    "altnames": {
      "es": [
        "Londres"
      ],
      "it": [
        "Londra"
      ],
      ...
    },
    "timezone": "Europe/London",
    "population": 8961989,
    "altitude": "",
    "country": "GB",
    "country_name": "United Kingdom",
    "state": "England",
    "county": "",
    "capital": "London",
    "continent": "EU",
    "currency_code": "GBP",
    "currency_name": "Pound",
    "phone": "44",
    "languages": "en-GB,cy-GB,gd",
    "neighbours": "IE"
  }
```

## Sources

[GeoNames](https://www.geonames.org/datasources/): All data except States and Counties.

[Geocoding](https://geocode.maps.co/): States and Counties.

## Licence

[Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/)
