import asyncio
import csv
import os
import urllib.request
import zipfile

import aiohttp
import requests
from bs4 import BeautifulSoup
from requests_html import HTMLSession

site = "https://www.zsc2.com/manhua/wojialaopolaiziyiqiannianqian/"
book_name = "我家老婆来自一千年前"


def yoink_page(url: str, retries=3):
    for tries in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
            page = requests.get(site, headers=headers)

            return page

        except:
            print(f"Error in fetching {url}")
            print(f"Retrying, attempt {tries}")

    return None


def fetch_chapters_urls(site: str):
    soup = BeautifulSoup(yoink_page(site).text, 'html.parser')

    chapter_list = soup.find("div", id="chapters").find("ul", id="chapter-list-1")

    with open("chapters.csv", mode="w", encoding="utf-8") as output:
        csv_writer = csv.writer(output)

        for link in chapter_list.find_all("a"):
            chapter_name = link.text.strip()
            url = site + link['href'][1:]
            csv_writer.writerow([chapter_name, url])


def download_chapters():
    with open("chapters.csv", mode="r", encoding="utf-8") as input:
        if not os.path.exists(book_name):
            os.mkdir(book_name)
        os.chdir(book_name)

        csv_reader = csv.reader(input)

        for row in csv_reader:

            # Skip empty rows
            if row == []:
                continue

            chapter_name = row[0]
            url = row[1]

            # make folder for each chapter
            if not os.path.exists(os.path.join(chapter_name)):
                os.mkdir(os.path.join(chapter_name))

            # download each chapter
            print(f"Downloading chapter {chapter_name}, url: {url}")
            book = asyncio.run(parse_chapter_async(url, chapter_name))


def parse_chapter(url: str, chapter_name: str, pause=0.1) -> list[dict]:
    session = HTMLSession()
    r = session.get(url)
    session.close()
    soup = BeautifulSoup(r.html.html, 'html.parser')
    images = soup.find("div", style="width:1px; height:0; overflow:hidden;").find_all("img")

    count = 0
    for image in images:
        count += 1

        url = image['data-src']
        image_extension = url.split('.')[-1]

        print(f"Downloading image {count}, url: {url}")

        file_name = os.path.join(chapter_name, f"{book_name}-{chapter_name}-{count}.{image_extension}")

        if os.path.exists(file_name):
            print("Chapter found, skipping...")
            continue

        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent',
                              'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36')]
        urllib.request.install_opener(opener)

        urllib.request.urlretrieve(url, file_name)


async def parse_chapter_async(url: str, chapter_name: str, pause=0.1) -> list[dict]:
    session = HTMLSession()
    r = session.get(url)
    session.close()
    soup = BeautifulSoup(r.html.html, 'html.parser')
    images = soup.find("div", style="width:1px; height:0; overflow:hidden;").find_all("img")

    tasks = []
    count = 0
    for image in images:
        count += 1
        tasks.append(asyncio.create_task(async_download_image(image, chapter_name, count)))
        # await async_download_image(image, chapter_name, count)
    await asyncio.gather(*tasks)


async def async_download_image(image, chapter_name, count):
    url = image['data-src']
    image_extension = url.split('.')[-1]

    print(f"Downloading image {count}, url: {url}")

    file_name = os.path.join(chapter_name, f"{book_name}-{chapter_name}-{count}.{image_extension}")

    if os.path.exists(file_name):
        print("Chapter found, skipping...")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            content = await response.read()

    with open(file_name, 'wb') as f:
        f.write(content)


def make_book():
    print("Making book:")
    with zipfile.ZipFile(f"{book_name}.cbz", mode="w") as archive:
        for root, dirs, files in os.walk(book_name):
            for file in files:
                file_path = os.path.join(root, file)
                print(f"Zipping file {file_path}")
                archive.write(file_path)

fetch_chapters_urls(site)
download_chapters()
make_book()