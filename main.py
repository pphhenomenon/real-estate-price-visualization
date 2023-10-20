from concurrent.futures import ThreadPoolExecutor

from constants import REGIONS
from data_collector.collector import DataCollector
from data_processor.processor import DataProcessor

with ThreadPoolExecutor(len(REGIONS)) as executor:
    results = executor.map(
        DataCollector.region_offers,
        (DataCollector(region) for region in REGIONS)
    )

for region, result in zip(REGIONS, results):
    instance = DataProcessor(region, result)
    instance.create_heat_map()
    instance.create_average_price_graph()
    instance.create_average_area_graph()
