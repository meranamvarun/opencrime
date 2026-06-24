"""Central registry mapping state codes to spider classes.

Adding a new state:
  1. Write a spider in spiders/<state>.py
  2. Import it here and add to SPIDER_REGISTRY

Populated district list lives on each spider class — the registry only
needs the class reference.
"""
from __future__ import annotations

from typing import Type

from app.crawler.base import BaseSpider
from app.crawler.spiders.up_police import UPPoliceSpider
from app.crawler.spiders.delhi_police import DelhiPoliceSpider
from app.crawler.spiders.maharashtra_police import MaharashtraPoliceSpider
from app.crawler.spiders.karnataka_police import KarnatakaPoliceSpider
from app.crawler.spiders.rajasthan_police import RajasthanPoliceSpider
from app.crawler.spiders.tamilnadu_police import TamilNaduPoliceSpider
from app.crawler.spiders.telangana_police import TelanganaPoliceSpider
from app.crawler.spiders.gujarat_police import GujaratPoliceSpider

SPIDER_REGISTRY: dict[str, Type[BaseSpider]] = {
    "UP": UPPoliceSpider,
    "DL": DelhiPoliceSpider,
    "MH": MaharashtraPoliceSpider,
    "KA": KarnatakaPoliceSpider,
    "RJ": RajasthanPoliceSpider,
    "TN": TamilNaduPoliceSpider,
    "TS": TelanganaPoliceSpider,
    "GJ": GujaratPoliceSpider,
}


def all_district_pairs() -> list[tuple[str, str]]:
    """Return every (state_code, district) pair across all registered spiders."""
    pairs = []
    for code, cls in SPIDER_REGISTRY.items():
        for district in cls.districts:
            pairs.append((code, district))
    return pairs


def district_count() -> int:
    return sum(len(cls.districts) for cls in SPIDER_REGISTRY.values())
