import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

CIAN_API_URL = "https://api.cian.ru/search-offers/v2/search-offers-desktop/"

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36",
    "referer": "https://www.cian.ru"
}

CIAN_REQUEST_DELAY = (2, 5)

MAX_PAGE_NUMBER = 55



class DataCollector(object):
    def __init__(self, region_params: dict) -> None:
        """Initialize the required attributes for the instance.

        Arguments:
            region_params {dict} -- region parameters:
                suffix {str}, base_site {str}, latitude {float}, longitude {float}
        """
        self.region_code = self.__region_code(region_params["base_site"])
        self.district_codes = self.__district_codes(region_params["base_site"])

    @staticmethod
    def __region_code(base_site: str) -> int:
        """Returns the region code using the region's base page code.

        Arguments:
            base_site {str} -- region's base site

        Returns:
            int -- region code
        """
        response = requests.get(base_site, headers=HEADERS)
        print(response.status_code)
        soup = BeautifulSoup(response.text, "lxml")
        target = soup.find("a", {"class": "_025a50318d--button--light--avRjM"})

        link = target.get("href")
        start = link.find("region")
        stop = link[start:].find("&")

        return int(link[start:][:stop].split("=")[1])

    @staticmethod
    def __district_codes(base_site: str) -> list:
        """Returns the region's list of district codes
        using the region's base page code.

        Arguments:
            base_site {str} -- region's base site

        Returns:
            list -- region's list of district codes
        """
        response = requests.get(base_site, headers=HEADERS)
        soup = BeautifulSoup(response.text, "lxml")
        sections = soup.find_all(
            "div", {"class": "_025a50318d--c-geo-section-items--Bmm9o"}
        )
        targets = sections[3].find_all(
            "div", {"class": "_025a50318d--c-geo-row--LaiuJ"}
        )

        codes = []

        for target in targets:
            districts = target.find_all(
                "a", {"class": "_025a50318d--c-geo-link--P1DwD"}
            )
            for district in districts:
                link = district.get("href")
                code = link[link.find("4") + 1: -1]
                codes.append(code)

        return list(map(int, filter(lambda code: code.isdigit(), codes)))

    @staticmethod
    def __create_payload(
        region_code: int, district_code: int, page_number: int
    ) -> dict:
        """Create the payload for the POST request.

        Arguments:
            region_code {int} -- region code
            district_code {int} -- district code
            page_number {int} -- page number

        Returns:
            dict -- payload
        """
        return {
            "jsonQuery": {
                "_type": "flatsale",
                "region": {
                    "type": "terms",
                    "value": region_code
                },
                "geo": {
                    "type": "geo",
                    "value": [
                        {
                            "type": "district",
                            "id": district_code
                        }
                    ]
                },
                "page": {
                    "type": "term",
                    "value": page_number
                },
                "engine_version": {
                    "type": "term",
                    "value": 2
                }
            }
        }

    @staticmethod
    def __offer_data(offer: dict) -> tuple:
        """Return the required offer data going through
        the corresponding keys in the dictionary.

        Arguments:
            offer {dict} -- offer

        Returns:
            tuple -- offer data: county {str}, latitude {float},
                longitude {float}, price {float}, area {str}
        """
        county = offer["geo"]["districts"][0]["name"]
        latitude = offer["geo"]["coordinates"]["lat"]
        longitude = offer["geo"]["coordinates"]["lng"]
        price = offer["bargainTerms"]["price"]
        area = offer["totalArea"]

        return county, latitude, longitude, price, area

    @staticmethod
    def __record_offer_data(
        coords: str, offers: dict, county: str, repeats: dict,
        area: str, price: float, latitude: float, longitude: float
    ) -> None:
        """
        Record offer data. If there is already the offer with such coordinates,
        the values of prices per meter and areas add up and the number of repeats
        increases. The number of repeats is used in the __process_offers function.

        args:
            coords {str} -- coordinates, where the house is located
            offers {dict} -- structure that contains the data of all offers
            county {str} -- county, where the house is located
            repeats {dict} -- structure that contains the data of all repeats
            area {str} -- flat area
            price {float} -- flat price
            latitude {float} -- latitude, where the house is located
            longitude {float} -- longitude, where the house is located
        """
        if coords in offers[county]:
            offers[county][coords]["area"] += float(area)
            offers[county][coords]["price_per_meter"] += price / float(area)
            repeats[county][coords] = repeats[county].get(coords, 1) + 1
            return
        offers[county][coords] = {
            "latitude": latitude,
            "longitude": longitude,
            "area": float(area),
            "price_per_meter": price / float(area)
        }

    @staticmethod
    def __process_offers(repeats: dict, offers: dict) -> dict:
        """
        Calculate the average value of prices per meter and areas for
        offers with the same coordinates and return the processed data.

        Arguments:
            repeats {dict} -- structure that contains the data of all repeats
            offers {dict} -- structure that contains the data of all offers

        Returns:
            dict -- structure that contains the data of all offers
        """
        for county in repeats:
            for coords in repeats[county]:
                offers[county][coords]["area"] /= repeats[county][coords]
                offers[county][coords]["price_per_meter"] /= repeats[county][coords]
        return offers

    def __district_offers(self, district_code: int) -> dict:
        """Return the data of the district's offers. Subsequently,
        the __region_offers function is used, passing through all
        districts to collect offer data for the entire region.

        Arguments:
            district_code {int} -- district code

        Returns:
            dict -- structure that contains the data of all district offers
        """
        offers, repeats = defaultdict(dict), defaultdict(dict)

        for page_number in range(1, MAX_PAGE_NUMBER):
            payload = self.__create_payload(self.region_code, district_code, page_number)  # noqa: E501
            response = requests.post(CIAN_API_URL, headers=HEADERS, json=payload)
            items = response.json()["data"]["offersSerialized"]

            if not items:
                return self.__process_offers(repeats, offers)

            for item in items:
                county, latitude, longitude, price, area = self.__offer_data(item)
                coords = "{}, {}".format(latitude, longitude)
                self.__record_offer_data(
                    coords, offers, county, repeats, area, price, latitude, longitude
                )

            time.sleep(random.randrange(*CIAN_REQUEST_DELAY))
        return self.__process_offers(repeats, offers)

    def region_offers(self) -> dict:
        """Return region offer data. The multithreading used here allows
        for asynchronous calculations in order to reduce the running time.

        Returns:
            dict -- region offer data
        """
        offers = defaultdict(dict)

        with ThreadPoolExecutor(len(self.district_codes)) as executor:
            results = executor.map(self.__district_offers, self.district_codes)

        for result in results:
            for county in result:
                offers[county].update(result[county])
        return offers


if __name__ == '__main__':
    DataCollector({
        "suffix": "spb",
        "base_site": "https://spb.cian.ru",
        "latitude": 59.939099,
        "longitude": 30.315877
    }).region_offers()
