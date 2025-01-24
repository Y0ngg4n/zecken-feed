import csv
import tempfile
from abc import ABC
import requests
import os
from platformdirs import user_cache_dir
from datetime import datetime, date
from feedgen.feed import FeedGenerator
from fastapi import FastAPI, Response


class Collector:
    demos = []
    feed: str

    def start(self):
        self.demo = []
        taz = Taz()
        taz.get_data()

    def convert_data_to_rss(self):
        fg = FeedGenerator()
        fg.id("ZeckenFeed")
        fg.title("Demos gegen Rechts")
        fg.description("Demos gegen Rechts")
        fg.author({"name": "TAZ"})
        fg.link(
            href="https://taz.de/Schwerpunkt-Demos-gegen-rechts/!t5338539/", rel="self"
        )
        fg.language = "en"
        for demo in self.demos:
            fe = fg.add_entry(order="append")
            fe.id(demo.getId())
            fe.title(f"{demo.place}")
            fe.description(f"{demo.startPoint} - {demo.date} {demo.time}")
        self.feed = fg.rss_str(pretty=True)

    def write_demos():
        pass


class Demo:
    place: str
    startPoint: str
    date: date
    time: str
    link: str

    def __init__(self, place, startPoint, date, time, link) -> None:
        self.place = place
        self.startPoint = startPoint
        self.date = date
        self.time = time
        self.link = link

    def getId(self):
        return (
            f"{self.place}#{self.startPoint}#{self.date.strftime("%d.%m.%Y")}".strip()
        )

    def __eq__(self, value: object, /) -> bool:
        return self.getId() == value


class Scraper(ABC):
    def get_data():
        pass


class Taz(Scraper):

    def __init__(self):
        self.counter = 839
        self.updateUrl()

    def updateCounter(self):
        pass

    def updateUrl(self):
        self.url = f"https://datawrapper.dwcdn.net/p3Ttm/{self.counter}/dataset.csv"

    def get_data(self):
        with requests.Session() as s:
            csv_response = s.get(self.url)
            if csv_response.status_code == 200:
                csv_response = csv.reader(csv_response.text.splitlines(), delimiter=",")
                csv_response = list(csv_response)
                for i in range(1, len(csv_response)):
                    Collector.demos.append(
                        Demo(
                            csv_response[i][0],
                            csv_response[i][1],
                            datetime.strptime(csv_response[i][2].strip(), "%d.%m.%Y"),
                            csv_response[i][3],
                            csv_response[i][4],
                        )
                    )
            else:
                self.counter += 1


app = FastAPI()

collector = Collector()
collector.start()
collector.convert_data_to_rss()


@app.get("/")
async def root():
    return Response(content=collector.feed, media_type="application/xml")
