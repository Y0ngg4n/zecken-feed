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
from dotenv import load_dotenv
from signalbot import SignalBot
import asyncio

load_dotenv()

counter_file = "./data/counter.txt"
data_file = "./data/data.csv"
cache_file = "./data/cache.txt"
old_data_file = "./data/data-old.csv"
data_dir = "./data"


class Collector:
    demos = []
    feed: str

    async def start(self):
        self.demo = []

        if not os.path.isdir(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        taz = Taz()
        await taz.get_data()

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
    latitude: float
    longitude: float

    def __init__(
        self, place, startPoint, date, time, link, latitude, longitude
    ) -> None:
        self.place = place
        self.startPoint = startPoint
        self.date = date
        self.time = time
        self.link = link
        self.latitude = latitude
        self.longitude = longitude

    def getId(self):
        date = self.date.strftime("%d.%m.%Y")
        return f"{self.place}#{self.startPoint}#{date}".strip()

    def __eq__(self, value: object, /) -> bool:
        return self.getId() == value


class Scraper(ABC):
    def get_data():
        pass


class Taz(Scraper):

    def __init__(self):
        self.counter = 913
        self.updateUrl()
        self.updateCounter()

    def updateCounter(self):
        global counter_file
        global data_file
        global old_data_file

        if os.path.isfile(counter_file):
            with open(counter_file, "r") as f:
                try:
                    self.counter = int(f.readline().strip())
                    print("Updated Counter to " + str(self.counter))
                except Exception as e:
                    print(e)
                    pass

    def updateUrl(self) -> str:
        self.url = f"https://datawrapper.dwcdn.net/p3Ttm/{self.counter}/dataset.csv"

    async def get_data(self):
        global counter_file
        global data_file
        global old_data_file
        self.updateCounter()
        csv_response = requests.get(self.url)
        while csv_response.status_code == 200:
            self.updateUrl()
            print(self.url)
            csv_response = requests.get(self.url)
            self.counter += 1
            time.sleep(1)

        self.counter -= 2
        self.updateUrl()
        with open(counter_file, "w") as f:
            f.write(str(self.counter))
        csv_response = requests.get(self.url)

        if not os.path.isfile(data_file):
            os.mknod(data_file)
        else:
            with open(data_file, mode="r") as fi:
                with open(old_data_file, mode="w") as fw:
                    fw.write(fi.read())

        with open(data_file, "w") as f:
            f.write(csv_response.text)
        csv_response = list(csv.reader(csv_response.text.splitlines(), delimiter=","))

        if os.path.isfile(old_data_file):
            with open(file=old_data_file, mode="r") as old:
                old_csv = list(csv.reader(old.read().splitlines(), delimiter=","))
                diff = list(set(map(tuple, csv_response)) - set(map(tuple, old_csv)))
                print(diff)
                bot = SignalBot(
                    {
                        "signal_service": os.environ["SIGNAL_SERVICE"],
                        "phone_number": os.environ["PHONE_NUMBER"],
                    }
                )
                # await bot.send(os.environ["GROUP"], "Test")

                if not os.path.isfile(cache_file):
                    os.mknod(cache_file)
                with open(cache_file, mode="r") as fw:
                    for item in diff.copy():
                        demo = Demo(
                            item[0],
                            item[1],
                            datetime.strptime(item[2].strip(), "%d.%m.%Y"),
                            item[3],
                            item[6],
                            item[4],
                            item[5],
                        )
                        if demo.getId() in fw.read():
                            diff.remove(item)

                if len(diff) > 2:
                    message = ""
                    for item in diff:
                        message += (
                            f"**{item[0]}**\n"
                            + f"*{item[2]} {item[3]}*\n"
                            + item[1]
                            + "\n"
                            + item[6]
                            + "\n-----\n"
                        )
                    await bot.send(os.environ["GROUP"], message)
                else:
                    for item in diff:
                        await bot.send(
                            os.environ["GROUP"],
                            f"**{item[0]}**\n"
                            + f"*{item[2]} {item[3]}*\n"
                            + item[1]
                            + "\n"
                            + item[6],
                        )

                with open(file=cache_file, mode="w") as fw:
                    for item in diff:
                        demo = Demo(
                            item[0],
                            item[1],
                            datetime.strptime(item[2].strip(), "%d.%m.%Y"),
                            item[3],
                            item[6],
                            item[4],
                            item[5],
                        )
                        fw.write(demo.getId())

        for i in range(1, len(csv_response)):
            Collector.demos.append(
                Demo(
                    csv_response[i][0],
                    csv_response[i][1],
                    datetime.strptime(csv_response[i][2].strip(), "%d.%m.%Y"),
                    csv_response[3],
                    csv_response[i][6],
                    csv_response[i][4],
                    csv_response[i][5],
                )
            )


collector = Collector()

app = FastAPI()


@app.get("/")
async def root():
    await collector.start()
    collector.convert_data_to_rss()
    return Response(content=collector.feed, media_type="application/xml")
