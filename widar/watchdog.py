from urllib.parse import urljoin
from uuid import uuid4

from bs4 import BeautifulSoup
from requests import get
import telegram
from telegram.ext import run_async

from query import Query, Metrazh
from state import State, Place
from ad import Ad


class Watchdog:

    def __init__(self, query, chat):
        self.query = query
        self.chat = chat
        self.history = set()
        self._job_name = None

    @property
    def job_name(self):
        if not self._job_name:
            self._job_name = uuid4()
        return self._job_name

    def __repr__(self):
        return f'{self.query}'+ str(id(self))[-5:]

    def start_job(self, job_queue):
        job = job_queue.run_repeating(self.fetch_ads, 30, name=self.job_name)
        return job

    @run_async
    def send(self, ad):
        msg = self.chat.send_message(
            ad.to_message(),
            parse_mode=telegram.ParseMode.HTML,
        )

        try:
            msg.reply_media_group(
                media=ad.media[:max(10, len(ad.media))]
            )
        except:
            pass


    @run_async
    def fetch_ads(self, context):
        print('fetch query')
        print('query: ', self.query.url)
        html_doc = get(self.query.url).text
        soup = BeautifulSoup(html_doc, 'html.parser')
        ads = soup.find_all('a', {'class': 'post-card-link'})
        ad_links = [ad['href']for ad in ads]
        new_ads = set(ad_links) - self.history
        print('len ads:', len(new_ads))

        if not self.history:
            self.history = new_ads
            return

        for ad_url in new_ads:
            url = urljoin(self.query.base_url, ad_url)
            ad = Ad(url=url)
            ad.fetch()
            self.send(ad)
            self.history.add(ad_url)

        return new_ads


