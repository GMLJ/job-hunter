"""Job scrapers package."""

from .base import BaseScraper, Job
from .reliefweb import ReliefWebScraper
from .ethiojobs import EthioJobsScraper
from .unjobs import UNJobsScraper
from .devex import DevExScraper
from .developmentaid import DevelopmentAidScraper

__all__ = [
    "BaseScraper",
    "Job",
    "ReliefWebScraper",
    "EthioJobsScraper",
    "UNJobsScraper",
    "DevExScraper",
    "DevelopmentAidScraper",
]

def get_all_scrapers():
    """Return instances of all available scrapers."""
    return [
        ReliefWebScraper(),
        EthioJobsScraper(),
        UNJobsScraper(),
        DevExScraper(),
        DevelopmentAidScraper(),
    ]
