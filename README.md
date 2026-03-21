# percival-osm

> A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that connects AI assistants to [OpenStreetMap](https://www.openstreetmap.org/), enabling real-time geospatial queries, point-of-interest discovery, and navigation — developed as a component of [percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS_Dev).

---

## Overview

**percival-osm** gives your AI agent the ability to explore the physical world. It provides a rich set of MCP tools backed by the Overpass API (OpenStreetMap data), Nominatim (geocoding), and OpenRouteService (routing), all without requiring any proprietary map API.

This project is derived from [lowlyocean/mcp-osm](https://github.com/lowlyocean/mcp-osm), which was itself based on [projectmoon's OSM tool for Open-WebUI](https://git.agnos.is/projectmoon/open-webui-filters/src/branch/master/osm.py). percival-osm extends the original work with Docker support, improved configuration, and integration with the percival.OS agent ecosystem.

---

## Features

- 🗺️ **Geocoding** — Reverse-geocode coordinates to human-readable addresses
- 📍 **POI Search** — Find points of interest near any place or GPS coordinates
- 🧭 **Navigation** — Get driving, cycling, or walking routes between locations
- 🐳 **Docker-ready** — Ships with `Dockerfile` and `docker-compose.yml`
- 🔌 **MCP-native** — Works out of the box with any MCP-compatible AI agent (nanobot, Claude Desktop, etc.)
- 🆓 **No proprietary APIs** — Powered entirely by open-source and free-tier services

---

## MCP Tools

| Tool | Description |
|---|---|
| `find_address_for_coordinates` | Reverse geocode GPS coordinates to an address |
| `find_store_or_place_near_coordinates` | Search for any type of place near coordinates |
| `find_specific_place` | Find a specific named place by name and city |
| `navigate_between_places` | Get route directions between two places |
| `find_grocery_stores_near_place` | Find supermarkets and grocery stores |
| `find_bakeries_near_place` | Find bakeries and bread shops |
| `find_food_near_place` | Find restaurants, cafés, and eateries |
| `find_swimming_near_place` | Find swimming pools and beaches |
| `find_playgrounds_near_place` | Find parks and playgrounds |
| `find_recreation_near_place` | Find gyms, sports centers, leisure activities |
| `find_tourist_attractions_near_place` | Find museums, monuments, and sights |
| `find_place_of_worship_near_place` | Find churches, mosques, synagogues, etc. |
| `find_accommodation_near_place` | Find hotels, hostels, and lodging |
| `find_alcohol_near_place` | Find bars, pubs, and liquor stores |
| `find_schools_near_place` | Find schools and primary education |
| `find_universities_near_place` | Find universities and colleges |
| `find_libraries_near_place` | Find public libraries |
| `find_public_transport_near_place` | Find bus stops, metro stations, etc. |
| `find_bike_rentals_near_place` | Find bicycle rental stations |
| `find_car_rentals_near_place` | Find car rental agencies |
| `find_hardware_store_near_place` | Find hardware and home improvement stores |
| `find_electrical_store_near_place` | Find electrical and lighting stores |
| `find_electronics_store_near_place` | Find consumer electronics stores |
| `find_doctor_near_place` | Find doctors and clinics |
| `find_hospital_near_place` | Find hospitals |
| `find_pharmacy_near_place` | Find pharmacies and health stores |
| `find_drugs_near_place` | Find pharmacies (alias) |
| `find_other_things_near_place` | Catch-all tool for unsupported categories |

---

## Requirements

- Python 3.11+
- An [OpenRouteService API key](https://openrouteservice.org/dev) (free tier available)
- Internet access to Nominatim and Overpass API (no API keys required)

---

## Installation

### Using `uv` (recommended)

```bash
git clone https://github.com/bill-kopp-ai-dev/percival-osm.git
cd percival-osm
uv sync
```

### Using `pip`

```bash
git clone https://github.com/bill-kopp-ai-dev/percival-osm.git
cd percival-osm
pip install -e .
```

---

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required for routing features
ORS_API_KEY=your-openrouteservice-api-key

# Nominatim configuration (use a descriptive user agent)
user_agent=percival-osm/1.0 (your-email@example.com)
from_header=your-email@example.com

# API endpoints (defaults work for public instances)
nominatim_url=https://nominatim.openstreetmap.org/
overpass_turbo_url=https://overpass-api.de/api/interpreter

# Behavior flags
instruction_oriented_interpretation=True
car_only=False
status_indicators=False
```

---

## Running

### Directly with Python

```bash
python osm.py
```

### With Docker

```bash
docker-compose up -d
```

---

## Integrating with nanobot / Claude Desktop

Add the following entry to your `config.json`:

```json
"percival-osm": {
  "command": "/path/to/.venv/bin/python",
  "args": ["/path/to/percival-osm/osm.py"],
  "env": {
    "user_agent": "percival-osm/1.0",
    "from_header": "your-email@example.com",
    "nominatim_url": "https://nominatim.openstreetmap.org/",
    "overpass_turbo_url": "https://overpass-api.de/api/interpreter",
    "instruction_oriented_interpretation": "True",
    "car_only": "False",
    "status_indicators": "False",
    "ORS_API_KEY": "your-openrouteservice-api-key"
  }
}
```

---

## Attribution

This project is built upon the work of:

- **[lowlyocean/mcp-osm](https://github.com/lowlyocean/mcp-osm)** — The direct upstream, providing the original MCP wrapper and Docker setup.
- **[projectmoon's OSM tool for Open-WebUI](https://git.agnos.is/projectmoon/open-webui-filters/src/branch/master/osm.py)** — The original OSM query engine on which `mcp-osm` was based.
- **[OpenStreetMap contributors](https://www.openstreetmap.org/copyright)** — All map data is © OpenStreetMap contributors, available under the [ODbL license](https://opendatacommons.org/licenses/odbl/).
- **[Nominatim](https://nominatim.org/)** — Open-source geocoding powered by OSM data.
- **[OpenRouteService](https://openrouteservice.org/)** — Open routing engine for directions and navigation.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.