import scrapy
import json
import math
import logging
from urllib.parse import urlencode
from datetime import datetime
import uuid
import base64
import csv
import time
from random import uniform
import math


KEYWORDS = ["white onion"]
US_ITEM_ID = "51259208"
WALMART_STORES_FILEPATH = "walmart_stores.csv"
SLEEP_TIMER_SECONDS = 5

class LocationMocker:
    def location_cookie(store_id, postal_code):
        timestamp = int(datetime.utcnow().strftime("%s"))
        acid = uuid.uuid4()

        location_guest_data = {
            "intent": "SHIPPING",
            "storeIntent": "PICKUP",
            "mergeFlag": True,
            "pickup": {
                "nodeId": store_id,
                "timestamp": timestamp
            },
            "postalCode": {
                "base": postal_code,
                "timestamp": timestamp
            },
            "validateKey": f"prod:v2:{acid}"
        }

        encoded_location_data = base64.b64encode(json.dumps(location_guest_data).encode('utf-8'))

        return dict(
                    ACID=str(acid),
                    hasACID='true',
                    hasLocData='1',
                    locDataV3=json.dumps(location_guest_data),
                    assortmentStoreId=store_id,
                    locGuestData=encoded_location_data.decode('utf-8')
                )

class ItemSpider(scrapy.Spider):
    name = "item"
    logger = logging.getLogger(__name__)

    def start_requests(self):
        # Keywords
        keyword_list = KEYWORDS

        with open(WALMART_STORES_FILEPATH, 'r') as csvfile:
            stores = csv.reader(csvfile)

            sleep_counter = 0

            for i, row in enumerate(stores):

                # Sleep longer if 50 requests have been completed.
                # Too lazy to write better callback functions :P
                if math.floor(i / 50) - sleep_counter > 0:
                    sleep_counter += 1
                    time.sleep(60 * 10)

                time.sleep(SLEEP_TIMER_SECONDS)
                location = (int(row[0]), int(row[1]))
                # For Idaho Falls
                # location = (1091, 36420)
                cookie = LocationMocker.location_cookie(location[0], location[1])
                store_dict = dict(store_id=row[0], postal_code=row[1], address=row[2])

                for keyword in keyword_list:
                    payload = {'q': keyword, 'sort': 'best_match', 'page': 1, 'affinityOverride': 'default'}
                    walmart_search_url = 'https://www.walmart.com/search?' + urlencode(payload)
                    self.logger.info(f"Making request to url - {walmart_search_url}")

                    self.logger.info(f"passing the following cookie to the request {cookie}")
                    yield scrapy.Request(
                        url=walmart_search_url,
                        cookies=cookie,
                        dont_filter=True,
                        callback=self.parse_filtered_result,
                        cb_kwargs=dict(store_dict=store_dict),
                        meta={'keyword': keyword, 'page': 1}
                    )

    def filter_product(self, product_list):
        return [i for i in product_list if 'usItemId' in i.keys() and i['usItemId'] == US_ITEM_ID]

    def parse_filtered_result(self, response, store_dict):

        page = response.meta['page']
        keyword = response.meta['keyword'] 
        script_tag  = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()

        if script_tag is not None:
            json_blob = json.loads(script_tag)

            ## This assumes that the White Onions, Each exists in the first page. Intuitively, it should
            ## since it's sorted by "best_match"
            product_list = json_blob["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["items"]
            filtered_product_list = self.filter_product(product_list)
            yield {
                'keyword': response.meta['keyword'],
                'product_name': filtered_product_list[0]['name'],
                'price': filtered_product_list[0]['price'],
                'unit_price': filtered_product_list[0]['priceInfo']['unitPrice'],
                'store_id': store_dict['store_id'],
                'postal_code': store_dict['postal_code'],
                'address': store_dict['address']
            }

    def parse_search_results(self, response):
        page = response.meta['page']
        keyword = response.meta['keyword'] 
        script_tag  = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)
            
            self.logger.info(json_blob)

            ## Request Product Page
            product_list = json_blob["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["items"]
            filtered_product_list = self.filter_product(product_list)
            for product in filtered_product_list:
                walmart_product_url = 'https://www.walmart.com' + product.get('canonicalUrl', '').split('?')[0]
                yield scrapy.Request(url=walmart_product_url, callback=self.parse_product_data, meta={'keyword': keyword, 'page': page})
            
            ## Request Next Page
            if page == 1:
                total_product_count = json_blob["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["count"]
                max_pages = math.ceil(total_product_count / 40)
                if max_pages > 25:
                    max_pages = 25
                for p in range(2, max_pages):
                    payload = {'q': keyword, 'sort': 'best_seller', 'page': p, 'affinityOverride': 'default'}
                    walmart_search_url = 'https://www.walmart.com/search?' + urlencode(payload)
                    yield scrapy.Request(url=walmart_search_url, callback=self.parse_search_results, meta={'keyword': keyword, 'page': p})

    def parse_product_data(self, response):
        script_tag  = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)
            raw_product_data = json_blob["props"]["pageProps"]["initialData"]["data"]["product"]
            yield {
                'keyword': response.meta['keyword'],
                'page': response.meta['page'],
                'id':  raw_product_data.get('id'),
                'type':  raw_product_data.get('type'),
                'name':  raw_product_data.get('name'),
                'brand':  raw_product_data.get('brand'),
                'averageRating':  raw_product_data.get('averageRating'),
                'manufacturerName':  raw_product_data.get('manufacturerName'),
                'shortDescription':  raw_product_data.get('shortDescription'),
                'thumbnailUrl':  raw_product_data['imageInfo'].get('thumbnailUrl'),
                'price':  raw_product_data['priceInfo']['currentPrice'].get('price'), 
                'currencyUnit':  raw_product_data['priceInfo']['currentPrice'].get('currencyUnit'),  
            }
