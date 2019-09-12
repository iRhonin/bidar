from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests import get

from .state import State

@dataclass
class Range:
    name: str
    slug: str
    from_: str = None
    to: str = None

    @property
    def code(self):
        code = ''
        if not self.from_ and not self.to:
            code = '0'
        elif not self.to:
            code = f'5,{self.from_}'
        elif not self.from_:
            code = f'3,{self.to}'
        else:
            code = f'1,{self.from_},{self.to}'

        return code

    def __str__(self):
        return f'v{self.slug}={self.code}'


class Query:

    def __init__(self, state, fields=[]):
        self.state = state
        self.fields = fields

    @property
    def url(self):
        url = urljoin(str(self.state), self.uri)
        url = f'{url}/?'

        for field in self.fields:
            url = f'{url}&{field}'

        return url


class EjareMaskan(Query):
    uri = 'browse/اجاره-مسکونی-آپارتمان-خانه-زمین/املاک-مسکن'


if __name__ == '__main__':
    tehran = State('تهران', 'tehran')
    ejare = EjareMaskan(state=tehran)
    metrazh = Range(name='متراژگ', slug='01', from_=10, to=100)
    ejare_m = Range(name='ejare', slug='10', from_=1000 * 1000)
    ejare.fields.append(metrazh)
    ejare.fields.append(ejare_m)
    print(ejare.url)
    html_doc = get('https://divar.ir/tehran/تهران/browse/').text
    soup = BeautifulSoup(html_doc, 'html.parser')

