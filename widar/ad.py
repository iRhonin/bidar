from browser import get_url
from bs4 import BeautifulSoup
from telegram import InputMediaPhoto


class Ad:
    def __init__(self, url):
        self.url = url
        self.title = ''
        self.desc = ''
        self.data = dict()

    def fetch(self):
        print(self.url)
        try:
            res = get_url(self.url)
            soup = BeautifulSoup(res, 'html.parser')
            self.title = soup.find('title').text
            self.desc = soup.find('p', {'class': 'kt-description-row__text kt-description-row__text--primary'}).text
            self.images = set(
                img['src']
                for img in soup.find_all('img', {'class': 'kt-image-block__image'})
            )
            items = soup.find_all('div', {'class': 'kt-base-row'})
            for item in items:
                try:
                    key = item.find('p', {'class': 'kt-base-row__title'}).text
                    value = item.find('p', {'class': 'kt-unexpandable-row__value'})
                    if value:
                        value = value.text
                    else:
                        value = item.find('div').text
                    self.data[key] = value
                except:
                    pass
        except Exception as ex:
            print(ex)

        print('####################################################################################')

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
