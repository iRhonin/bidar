from bs4 import BeautifulSoup
from dataclasses import dataclass
from requests import get
from telegram import InputMediaPhoto
from telegram.ext import run_async


class Ad:

    def __init__(self, url):
        self.url = url
        self.title = ''
        self.desc = ''
        self.data = dict()

    def fetch(self):
        res = get(self.url).text
        soup = BeautifulSoup(res, 'html.parser')

        self.title = soup.find('h1').text
        self.desc = soup.find('div', {'class': 'post-description'}).text
        self.images = set(
            img['src']
            for img in  soup.find_all('img', {'class': 'image-slider'})
        )
        items = soup.find_all('div', {'class': 'item'})

        for item in items:
            try:
                key = item.find('span').text
                value = item.find('a')
                if value:
                    value = value.text
                else:
                    value = item.find('div').text

                self.data[key] = value

            except:
                pass

    def to_message(self):
        res = f'{self.title}\n\n'
        for k,v in self.data.items():
            res += f'{k}: \b\t{v}\n'

        res += f'\n{self.desc}\n\n'
        res += self.url
        return res

    @property
    def media(self):
        return [
            InputMediaPhoto(img) for img in self.images
        ]
