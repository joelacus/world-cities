# World Cities Geolocation Data

Geolocation data for all of the cities in the world as json/csv.

[See Examples and Download](#examples-and-download)

You can [generate your own](#custom-lists) custom list with extra data with the python script.

_NPM install planned._

<br/>

## Examples and Download

<br/>

|Population Threshold|Meaning|
|----|----|
|1000|More precise. Villages, towns, and cities of 1000 or more in population. Bigger file size.|
|5000|Average. Towns and cities of 5000 or more in population.|
|15000|Least precise. Large towns, and cities of 15000 or more in population. Smaller file size.|

<br/>

#### Basic

<table>
<tr>
  <td> JSON example </td> <td> CSV example </td>
</tr>
<tr>
  <td>
  
  ```json
  [
    {
      "country": "GB",
      "name": "London",
      "lat": "51.50853",
      "lng": "-0.12574",
    },
    ...
  ]
  ```

  </td>
  <td>

    country,name,lat,lng
    GB,London,51.50853,-0.12574
    ...

  </td>
</tr>
</table>

|Population Threshold|Download JSON|Download CSV|
|----|----|----|
|1000|[world_cities.json]()|[world_cities.csv]()|
|5000|[world_cities_5000.json]()|[world_cities_5000.csv]()|
|15000|[world_cities_15000.json]()|[world_cities_15000.csv]()|

<br/>

#### Basic, including states for US only
<table>
<tr>
  <td> JSON example </td> <td> CSV example </td>
</tr>
<tr>
  <td>
  
  ```json
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
 
  </td>
  <td>

    country,state,name,lat,lng
    US,NY,New York City,40.71427,-74.00597
    ...

  </td>
</tr>
</table>

|Population Threshold|Download JSON|Download CSV|
|----|----|----|
|1000|[world_cities_(including_US_states).json]()|[world_cities_(including_US_states).csv]()|

<br/>

#### Basic, including states and counties for all countries

|Population Threshold|Download JSON|Download CSV|
|----|----|----|
|1000|[world_cities_(including_all_states_and_counties).json]()|[world_cities_(including_all_states_and_counties).csv]()|

<table>

<br/>

#### Basic, including states and counties for cities, in all countries, with the same name

|Population Threshold|Download JSON|Download CSV|
|----|----|----|
|1000|[world_cities_(including_states_and_counties_for_duplicate_names).json]()|[world_cities_(including_states_and_counties_for_duplicate_names).csv]()|

<table>

<br/>


#### Example with all data points


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
    "elevation": "23",
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
-   Elevation (metre)
-   Continent
-   Capital City
-   Currency Code
-   Currency Name
-   Phone Extension
-   Spoken Languages
-   Country Neighbours

A [free Geocoding API key](https://geocode.maps.co/join/) is now required to fetch 'state' and 'county' data.

## Sources

[GeoNames](https://www.geonames.org/datasources/): All data except States and Counties.

[Geocoding](https://geocode.maps.co/): States and Counties.

[Geo FCC](https://geo.fcc.gov/api/census): US Counties

[Open Meteo](https://open-meteo.com/): Elevation

## Licence

[Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/)
