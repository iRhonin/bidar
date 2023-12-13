from dataclasses import dataclass


class State:
    def __init__(self, name, slug):
        self.name = name
        self.slug = slug

    def __str__(self):
        return f'{self.slug}/'


@dataclass
class Place:
    name: str
    code: str
