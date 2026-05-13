# 🤖 Percival OSM - percival.OS MCP

**Version 0.0.2**

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)

## 📋 Description
**Percival OSM** is an MCP server that connects AI assistants to **OpenStreetMap**, enabling real-time geospatial queries, point-of-interest discovery, and navigation.

This server is part of the **percival.OS** ecosystem, a Personal Agentic Operating System designed for autonomy, security, and absolute privacy.

---

## 🛡️ percival.OS Principles
Like all components of `percival.OS`, this MCP server strictly follows our core principles:

- **Privacy & Governance**: Queries are made via open and respectful APIs (Nominatim, Overpass), without invasive commercial tracking.
- **Data Sovereignty**: Your coordinates and location queries remain under your operational control.
- **Hardened Security**: We implement compact responses to reduce token usage and structured safe outputs against manipulation.
- **Transparency**: Based on the `lowlyocean/mcp-osm` project, extended with security hardening and integration with the Percival ecosystem.

---

## 🚀 Features & Tools
The server offers a vast set of geospatial tools:

- `osm_find_nearby`: Search POIs by category (recommended for Nanobot).
- `osm_find_address`: Convert GPS coordinates to human-readable addresses.
- `osm_find_place`: Find a specific location by name and city.
- `osm_navigate`: Obtain route directions between two locations.
- **Category Tools**: `osm_find_groceries`, `osm_find_food`, `osm_find_doctors`, `osm_find_pharmacy`, etc.
- **Utility**: `osm_get_status`, `osm_get_security_metrics`.

---

## ⚙️ Configuration in percival.OS (Nanobot)
Add the following configuration to your `~/.nanobot/config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "percival-osm": {
        "command": "/path/to/.venv/bin/python",
        "args": ["-m", "percival_osm_mcp"],
        "env": {
          "user_agent": "percival-osm/1.0 (your-email@example.com)",
          "from_header": "your-email@example.com",
          "ORS_API_KEY": "your-openrouteservice-key",
          "OSM_RESPONSE_MODE": "compact"
        }
      }
    }
  }
}
```

---

## 🛠️ Development & Testing
This project uses the shared `percival.OS_Dev` virtual environment.

```bash
# Execution via shared environment
PYTHONPATH=src ../../.venv/bin/python -m percival_osm_mcp --mode stdio

# Run tests
uv run pytest -q
```

---

## 📚 About the Project
This server is an integral module of the **percival.OS** project. It allows Nanobot to interact with the physical world through OpenStreetMap's open data.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
