"""Baseline dataset for the portal.

PRODUCTION_SERIES holds the district-level figures supplied for this project.
Everything else here (capacity, harvest calendar, block split, coordinates) is a
planning ASSUMPTION and is labelled as such on the site. Replace those values
with official block-level data and the cold storage registry when available.
"""

DISTRICT = {
    "name": "Hathras",
    "state": "Uttar Pradesh",
    "crop": "Potato",
    "center": {"lat": 27.5968, "lng": 78.0519},
}

PRODUCTION_SERIES = [
    {"season": "2018-19", "area_ha": 51200, "production_t": 1218000, "yield_kg_ha": 23789},
    {"season": "2019-20", "area_ha": 52450, "production_t": 1261000, "yield_kg_ha": 24041},
    {"season": "2020-21", "area_ha": 53100, "production_t": 1298000, "yield_kg_ha": 24444},
    {"season": "2021-22", "area_ha": 54000, "production_t": 1312000, "yield_kg_ha": 24296},
    {"season": "2022-23", "area_ha": 54800, "production_t": 1351000, "yield_kg_ha": 24653},
    {"season": "2023-24", "area_ha": 55200, "production_t": 1362000, "yield_kg_ha": 24673},
]

DATA_SOURCE = {
    "label": "District potato area & production, Hathras (UP), 2018-19 to 2023-24",
    "note": (
        "Figures as supplied in the project brief. Cross-check against the UP Directorate "
        "of Horticulture / DES (Ministry of Agriculture) district APY releases before operational use."
    ),
}

# Share of the harvest that goes into cold storage (from the brief).
DEFAULT_STORAGE_RATIO = 0.75

# ASSUMPTION: aggregate cold storage capacity in the district, tonnes.
DEFAULT_REGIONAL_CAPACITY_T = 950_000

DEFAULT_ALERT_THRESHOLD = 0.9

# ASSUMPTIONS for holding economics; both are editable in the planners.
DEFAULT_KWH_PER_T_MONTH = 9.0      # electricity per tonne held per month
DEFAULT_TARIFF_RS_KWH = 7.5        # commercial power tariff, ₹ per kWh

# ASSUMPTION: share of the season's storage intake arriving each month.
# Hathras potatoes are dug late February through March; loading tails into April.
MONTHLY_INTAKE_PROFILE = {"Feb": 0.18, "Mar": 0.57, "Apr": 0.25}

# ASSUMPTION: share of stored stock released each month, May through November.
MONTHLY_RELEASE_PROFILE = {
    "May": 0.08, "Jun": 0.12, "Jul": 0.15, "Aug": 0.17,
    "Sep": 0.18, "Oct": 0.17, "Nov": 0.13,
}

# ASSUMPTION: development blocks, approximate HQ coordinates, and a modelled split
# of district production and storage capacity. Each share column sums to 1.
BLOCKS = [
    {"id": "hathras", "name": "Hathras", "lat": 27.5968, "lng": 78.0519, "production_share": 0.20, "capacity_share": 0.24},
    {"id": "sasni", "name": "Sasni", "lat": 27.7030, "lng": 78.0840, "production_share": 0.17, "capacity_share": 0.14},
    {"id": "sikandra-rao", "name": "Sikandra Rao", "lat": 27.6886, "lng": 78.3810, "production_share": 0.18, "capacity_share": 0.13},
    {"id": "sadabad", "name": "Sadabad", "lat": 27.4386, "lng": 78.0378, "production_share": 0.17, "capacity_share": 0.17},
    {"id": "mursan", "name": "Mursan", "lat": 27.5800, "lng": 77.9460, "production_share": 0.10, "capacity_share": 0.12},
    {"id": "sahpau", "name": "Sahpau", "lat": 27.4350, "lng": 78.1450, "production_share": 0.08, "capacity_share": 0.10},
    {"id": "hasayan", "name": "Hasayan", "lat": 27.7350, "lng": 78.2850, "production_share": 0.10, "capacity_share": 0.10},
]

ASSUMPTIONS = [
    {"item": "Share of harvest stored", "value": "75%", "status": "From brief", "note": "Adjustable in the capacity planner."},
    {"item": "District cold storage capacity", "value": "950,000 t", "status": "Assumption", "note": "Replace with the registered capacity from the UP Horticulture cold storage list."},
    {"item": "Monthly intake profile", "value": "Feb 18% · Mar 57% · Apr 25%", "status": "Assumption", "note": "Timing of loading into cold storage after digging."},
    {"item": "Monthly release profile", "value": "May–Nov, peaking Sep", "status": "Assumption", "note": "Timing of withdrawals for market and seed."},
    {"item": "Block production & capacity split", "value": "7 blocks", "status": "Assumption", "note": "Modelled shares; markers at approximate block HQ locations."},
    {"item": "Electricity use", "value": "9 kWh per tonne per month", "status": "Assumption", "note": "Used for holding-cost estimates. Replace with your facility's metered figure."},
    {"item": "Power tariff", "value": "₹7.5 per kWh", "status": "Assumption", "note": "Replace with your connection's tariff."},
    {"item": "Distances between blocks", "value": "Straight line", "status": "Approximation", "note": "Road distances are longer; add a road-distance matrix for routing."},
]
