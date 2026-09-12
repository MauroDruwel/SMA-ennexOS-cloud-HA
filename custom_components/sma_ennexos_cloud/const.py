DOMAIN = "sma_ennexos_cloud"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PLANT_ID = "plant_id"
CONF_PLANT_NAME = "plant_name"


# Options
CONF_POLL_INTERVAL = "poll_interval"
CONF_ENERGY_POLL_INTERVAL = "energy_poll_interval"

# Defaults
DEFAULT_POLL_INTERVAL = 30  # seconds – live power
DEFAULT_ENERGY_POLL_INTERVAL = 300  # seconds – daily energy (5 min)
MIN_POLL_INTERVAL = 10
MAX_POLL_INTERVAL = 300
MIN_ENERGY_POLL_INTERVAL = 60
MAX_ENERGY_POLL_INTERVAL = 3600
