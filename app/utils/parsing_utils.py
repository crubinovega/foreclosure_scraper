from bs4 import BeautifulSoup

def make_soup(html):
    return BeautifulSoup(html, "html.parser")
