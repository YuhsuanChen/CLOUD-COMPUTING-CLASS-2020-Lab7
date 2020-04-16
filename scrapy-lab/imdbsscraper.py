# -*- coding: utf-8 -*-
import os
import uuid

import scrapy
import unidecode as unidecode
import re

from scrapy import Selector
from elasticsearch import Elasticsearch

ELASTIC_API_URL_HOST = os.environ['ELASTIC_API_URL_HOST']
ELASTIC_API_URL_PORT = os.environ['ELASTIC_API_URL_PORT']
ELASTIC_API_USERNAME = os.environ['ELASTIC_API_USERNAME']
ELASTIC_API_PASSWORD = os.environ['ELASTIC_API_PASSWORD']

es=Elasticsearch(host=ELASTIC_API_URL_HOST,
                 scheme='https',
                 port=ELASTIC_API_URL_PORT,
                 http_auth=(ELASTIC_API_USERNAME,ELASTIC_API_PASSWORD))

cleanString = lambda x: '' if x is None else unidecode.unidecode(re.sub(r'\s+', ' ', x))
OutputList = []
OutputActors = []


class ImdbsscraperSpider(scrapy.Spider):
    name = 'imdbsscraper'
    allowed_domains = ['https://www.imdb.com']
    start_urls = ['https://www.imdb.com/title/tt0096463/fullcredits']

    def parse(self, response):
        OutputList.append(response.url)
        actor_url_list = []
        actor_name_list = []
        actor_id_list = []
        role_list = []
        actor_link_list = []

        for ActorID in response.css('table.cast_list td.primary_photo a::attr(href)').extract():
            actor_id_list.append(ActorID.replace("/name/", "").replace("/", ""))

        for link in response.css('table.cast_list td a').extract():
            actor_link_list.append(link)

        for actor in response.css('table.cast_list td a::text').extract():
            if actor not in response.css('table.cast_list td[class="character"] a::text').extract():
                actor_name_list.append(cleanString(actor))

        for role in response.css('table.cast_list td[class="character"]').extract():
            role = cleanString(role)
            role_split = role.split("""<td class="character">""", 2)[1].split("</td>", 2)[0].split("</a>", 2)[0].split(
                ">", 2)
            if len(role_split) == 2:
                role_split[0] = role_split[1]
            role_list.append(role_split[0])

        count = 0

        for actor in actor_name_list:
            yield {
                "movie_id": response.css('h3[itemprop="name"] a::attr(href)').extract_first().split("/")[2],
                "movie_name": response.css('h3[itemprop="name"] a::text').extract_first(),
                "movie_year": cleanString(response.css('h3[itemprop="name"] span::text').extract_first()).replace("(",
                                                                                                                  "").replace(
                    ")", ""),
                'actor_name': actor_name_list[count],
                'actor_id': actor_id_list[count],
                'role_name': role_list[count]
            }
            next_url = 'https://www.imdb.com/name/' + actor_id_list[count] + '/'  # actor url
            actor_url_list.append(next_url)
            count = count + 1

        for url in actor_url_list:
          #  if url not in OutputActors:
                request = scrapy.Request(url, callback=self.parse_next_movie, dont_filter=True)
                yield request

    def parse_next_movie(self, response):
        OutputActors.append(response.url)
        movie_in_80s = []
        next_movie_year = []
        next_movie_id = []
        next_movie_title = response.css('div.filmo-category-section div b a::text').extract()
        for movie in response.css('div.filmo-category-section div span.year_column::text').extract():
            next_movie_year.append(movie.replace("\n\u00a0", "").replace("\n", ""))

        for movie in response.css('div.filmo-category-section div b a::attr(href)').extract():
            next_movie_id.append(movie)

        result = zip(next_movie_id, next_movie_year)
        result_set = set(result)

        for i, j in result_set:
            j = j.split("/", 2)[0].split("-", 2)[0]
            if j == '':
                j = 0
            if 1980 < int(j) < 1990:
                url = 'https://www.imdb.com' + i + 'fullcredits'
                movie_in_80s.append(url)

        for url in movie_in_80s:
            if url not in OutputList:
                request2 = scrapy.Request(url, callback=self.parse2, dont_filter=True)
                yield request2

    def parse2(self, response):
        OutputList.append(response.url)
        actor_name_list = []
        actor_id_list = []
        role_list = []
        actor_link_list = []

        for ActorID in response.css('table.cast_list td.primary_photo a::attr(href)').extract():
            actor_id_list.append(ActorID.replace("/name/", "").replace("/", ""))

        for link in response.css('table.cast_list td a').extract():
            actor_link_list.append(link)

        for actor in response.css('table.cast_list td a::text').extract():
            if actor not in response.css('table.cast_list td[class="character"] a::text').extract():
                actor_name_list.append(cleanString(actor))

        for role in response.css('table.cast_list td[class="character"]').extract():
            role = cleanString(role)
            role_split = role.split("""<td class="character">""", 2)[1].split("</td>", 2)[0].split("</a>", 2)[0].split(
                ">", 2)
            if len(role_split) == 2:
                role_split[0] = role_split[1]
            role_list.append(role_split[0])

        count = 0

        for actor in actor_name_list:
            # yield { "movie_id": response.css('h3[itemprop="name"] a::attr(href)').extract_first().split("/")[2],
            # "movie_name": response.css('h3[itemprop="name"] a::text').extract_first(), "movie_year": cleanString(
            # response.css('h3[itemprop="name"] span::text').extract_first()).replace("(", "").replace( ")", ""),
            # 'actor_name': actor_name_list[count], 'actor_id': actor_id_list[count], 'role_name': role_list[count] }
            es.index(index='imdb',
                     doc_type='movies',
                     id=uuid.uuid4(),
                     body={
                         "movie_id": response.css('h3[itemprop="name"] a::attr(href)').extract_first().split("/")[2],
                         "movie_name": response.css('h3[itemprop="name"] a::text').extract_first(),
                         "movie_year": cleanString(
                             response.css('h3[itemprop="name"] span::text').extract_first()).replace("(","").replace(")", ""),
                         'actor_name': actor_name_list[count],
                         'actor_id': actor_id_list[count],
                         'role_name': role_list[count]
                     })

            count = count + 1

