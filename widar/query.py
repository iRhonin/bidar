from functools import partial
from urllib.parse import urljoin

from dataclasses import dataclass


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
            pass
        elif not self.to:
            code = f'5,{self.from_}'
        elif not self.from_:
            code = f'3,{self.to}'
        else:
            code = f'1,{self.from_},{self.to}'

        return code

    def is_empty(self):
        return not self.from_ and not self.to

    def __str__(self):
        return f'v{self.slug}={self.code}'


Metrazh = partial(Range, name='متراژ', slug='01')
Vadie = partial(Range, name='ودیعه', slug='09')
Ejare = partial(Range, name='اجاره', slug='10')


class Query:
    base_url = 'https://divar.ir/'

    def __init__(self, state, fields=[], places=[], near=False):
        self.state = state
        self.fields = fields
        self.places = places
        self.near = near

    def __str__(self):
        query = self.state.name

        if self.places:
            places = ''
            for place in self.places:
                places = f'{places}, {place.name}'
            query = f'{query}, {places}'

        return query + ' id:'+ str(id(self))[-4:]

    @property
    def url(self):
        url = self.base_url
        url = urljoin(url, str(self.state))
        url = urljoin(url, self.uri)
        url = f'{url}/?'

        for field in self.fields:
            if field.is_empty():
                self.fields.remove(field)
                continue

            url = f'{url}&{field}'

        if self.places:
            places = ''
            if self.near:
                places = 'place=8'
            else:
                places = 'place=6'

            for place in self.places:
                places = f'{places},{place.code}'
            url = f'{url}&{places}'

        return url


class EjareMaskan(Query):
    name = 'اجاره مسکن'
    uri = 'browse/اجاره-مسکونی-آپارتمان-خانه-زمین/املاک-مسکن'

    @property
    def metrazh(self):
        for f in self.fields:
            if f.name == 'متراژ':
                return f
        return

    @property
    def vadie(self):
        for f in self.fields:
            if f.name == 'ودیعه':
                return f
        return

    @property
    def ejare(self):
        for f in self.fields:
            if f.name == 'اجاره':
                return f
        return

