import os

import folium
from folium import plugins
from matplotlib import pyplot as plt

from .constants import (BARS_NUMBER, BASE_TILESET, DOTS_PER_INCH, RADIUS,
                        TILESETS, ZOOM_START)


class DataProcessor(object):
    def __init__(self, region_params: dict, region_offers: dict) -> None:
        """Initialize the required attributes for the instance.

        Arguments:
            region_params {dict} -- region parameters:
                suffix {str}, base_site {str}, latitude {float}, longitude {float}
            region_offers {dict} -- region offers
        """
        self.suffix = region_params["suffix"]
        self.latitude = region_params["latitude"]
        self.longitude = region_params["longitude"]
        self.region_offers = region_offers

    def create_heat_map(self) -> None:
        """Create the heat map of real estate prices, in which the
        color shows the price of real estate in terms of square meter.
        """
        city_map = folium.Map(
            location=[self.latitude, self.longitude], tiles=BASE_TILESET,
            zoom_start=ZOOM_START, control_scale=True
        )

        for tiles in TILESETS:
            folium.TileLayer(tiles).add_to(city_map)

        data = []

        for county, offers in self.region_offers.items():
            for coords, dataset in offers.items():
                latitude = dataset["latitude"]
                longitude = dataset["longitude"]
                price = dataset["price_per_meter"]
                data.append([latitude, longitude, price])

        city_heat_map = plugins.HeatMap(data, name="HEATMAP", radius=RADIUS, show=True)
        city_heat_map.add_to(city_map)

        folium.LayerControl().add_to(city_map)

        os.makedirs("maps", exist_ok=True)
        city_map.save("maps/{}_heat_map.html".format(self.suffix))

    def __average_county_prices(self) -> list:
        """Return the list of average prices of counties.

        Returns:
            list -- average prices of counties
        """
        average_prices = []

        for county, offers in self.region_offers.items():
            total_price = sum(offers[coords]["price_per_meter"] for coords in offers)
            average_price = total_price / len(offers)
            average_prices.append([county, average_price])

        return average_prices[:BARS_NUMBER]

    def __average_county_areas(self) -> list:
        """Return the list of average areas of counties.

        Returns:
            list -- average areas of counties
        """
        average_areas = []

        for county, offers in self.region_offers.items():
            total_area = sum(offers[coords]["area"] for coords in offers)
            average_area = total_area / len(offers)
            average_areas.append([county, average_area])

        return average_areas[:BARS_NUMBER]

    def create_average_price_graph(self) -> None:
        """Create average price graph.
        """
        average_prices = self.__average_county_prices()
        indices = list(range(len(average_prices)))
        counties, prices = zip(*average_prices)

        plt.figure()
        plt.bar(indices, prices, color="red")
        plt.xticks(indices, counties, rotation="vertical")
        plt.title("Средняя цена недвижимости за квадратный метр")
        plt.xlabel("Муниципальный округ")
        plt.ylabel("Цена, руб")
        plt.tight_layout()

        os.makedirs("charts", exist_ok=True)
        plt.savefig(
            "charts/{}_average_price_graph.png".format(self.suffix), dpi=DOTS_PER_INCH
        )

    def create_average_area_graph(self) -> None:
        """Create average area graph.
        """
        average_areas = self.__average_county_areas()
        indices = list(range(len(average_areas)))
        counties, areas = zip(*average_areas)

        plt.figure()
        plt.bar(indices, areas, color="red")
        plt.xticks(indices, counties, rotation="vertical")
        plt.title("Средняя площадь недвижимости")
        plt.xlabel("Муниципальный округ")
        plt.ylabel("Площадь, кв. м")
        plt.tight_layout()

        os.makedirs("charts", exist_ok=True)
        plt.savefig(
            "charts/{}_average_area_graph.png".format(self.suffix), dpi=DOTS_PER_INCH
        )
