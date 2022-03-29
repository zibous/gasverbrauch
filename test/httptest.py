#!/usr/bin/python3
# -*- coding":" utf-8 -*-

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# see: https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/

retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)

adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

response = http.get("http://wug2022.siebler.home/sensor/wug2_gaszhler_anzeige",timeout=10)
print(response.status_code,response.text)