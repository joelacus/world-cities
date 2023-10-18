# World Cities Geolocation Data
Geolocation data for all of the cities in the world as json/csv. [See Examples](#examples).

You can generate your own custom list with extra data with the python script.

*NPM install coming soon.*

## Custom Lists

To generate your own list, run `python get_world_cities.py` and follow the CLI prompts.

Available data:

- ISO-3166 2-letter country code
- Full country name
- State
- County
- City/place name
- Alternative names
- Latitude
- Longitude
- Timezone
- Population
- Altitude

You can choose whether you want to include cities/places with greater than '1000', '5000', or '15000' in population.

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
world_cities.csv
```
country,name,lat,lng
GB,London,51.50853,-0.12574
...
```
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
world_cities_(including_US_states).csv
```
country,state,name,lat,lng
US,NY,New York City,40.71427,-74.00597
...
```

## Sources
[GeoNames](https://www.geonames.org/datasources/): Country Code, City/Place Name, Alternative Names, Latitude, Longitude, Timezone, Population, and Altitude.

[Maps.co](https://geocode.maps.co/): States and Counties.

[annexare](https://github.com/annexare/Countries): Full Country Names.

## Licence
[Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/)
