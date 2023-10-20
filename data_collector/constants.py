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
