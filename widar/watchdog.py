import re
from urllib.parse import quote, urljoin
from uuid import uuid4

import telegram
from ad import Ad
from browser import get_url
from bs4 import BeautifulSoup
from telegram.ext import run_async


class Watchdog:

    def __init__(self, query, chat):
        self.query = query
        self.chat = chat
        self.history = set()
        self._job_name = None

    @property
    def job_name(self):
        if not self._job_name:
            self._job_name = str(uuid4())
        return self._job_name

    def __repr__(self):
        return f'{self.query}'+ str(id(self))[-5:]

    def start_job(self, job_queue):
        job = job_queue.run_repeating(self.fetch_ads, 60, name=self.job_name)
        return job

    @run_async
    def send(self, ad: Ad):
        ad.fetch()
        if len(ad.media) == 0:
            self.chat.send_message(
                ad.to_message(),
                parse_mode=telegram.ParseMode.HTML,
            )
            return

        media = ad.media[: max(10, len(ad.media))]
        media[0].caption = ad.to_message()
        self.chat.send_media_group(media=media)

    @run_async
    def fetch_ads(self, context):
        encoded_url = quote(self.query.url, safe=':/?=')
        print('fetch query: ', encoded_url)
        res = get_url(encoded_url)
        soup = BeautifulSoup(res, 'html.parser')
        ads = soup.find_all('div', {'class': re.compile(r'post\-card\-item')})
        hrefs = [div.find('a')['href'] for div in ads]
        new_ads = set(hrefs) - self.history
        print('len ads:', len(new_ads))
        print('history:', self.history)
        if not self.history:
            print('set history:', self.history)
            self.history = new_ads
            return

        for ad_url in new_ads:
            if ad_url in self.history:
                continue
            self.history.add(ad_url)
            url = urljoin(self.query.base_url, ad_url)
            ad = Ad(url=url)
            self.send(ad)

        return new_ads
