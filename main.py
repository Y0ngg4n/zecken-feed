import csv
import tempfile
from abc import ABC
import requests
import os
from platformdirs import user_cache_dir
from datetime import datetime, date
import time
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
        self.counter = 845
        self.updateUrl()
        self.updateCounter()

    def updateCounter(self):
        with open("counter.txt", "r") as f:
            try:
                self.counter = int.parse(f.readline())
            except:
                pass

        pass

    def updateUrl(self) -> str:
        self.url = f"https://datawrapper.dwcdn.net/p3Ttm/{self.counter}/dataset.csv"

    def get_data(self):
        csv_response = requests.get(self.url)
        while csv_response.status_code == 200:
            self.updateUrl()
            print(self.url)
            csv_response = requests.get(self.url)
            self.counter += 1
            time.sleep(1)

        self.counter -= 2
        self.updateUrl()
        with open("counter.txt", "w") as f:
            f.write(str(self.counter))
        csv_response = requests.get(self.url)

        if not os.path.isfile("data.csv"):
            with open("data.csv", "w") as f:
                f.write("")
        else:
            with open("data.csv", mode="r") as fi:
                with open("data-old.csv", mode="w") as fw:
                    fw.write(fi.read())

        with open("data.csv", "w") as f:
            f.write(csv_response.text)
        csv_response = list(csv.reader(csv_response.text.splitlines(), delimiter=","))

        if os.path.isfile("data-old.csv"):
            with open(file="data-old.csv", mode="r") as old:
                old_csv = list(csv.reader(old.read().splitlines(), delimiter=","))
                diff = list(set(map(tuple, csv_response)) - set(map(tuple, old_csv)))

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


collector = Collector()

app = FastAPI()


@app.get("/")
async def root():
    collector.start()
    collector.convert_data_to_rss()
    return Response(content=collector.feed, media_type="application/xml")
