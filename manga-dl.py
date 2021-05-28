import grequests
import requests
import os
from bs4 import BeautifulSoup as bs
import time
from threading import Thread
from eta import ETA
from colorama import Fore


def eta_loop():
    global ticks, message, total_ticks
    while ticks < total_ticks:
        eta.print_status(ticks, extra=Fore.GREEN+message+Fore.RESET)
        time.sleep(0.1)
    eta.done()


def format_for_url(s):
    return '_'.join(''.join(map(lambda x: x if x.isalnum() else ' ', s)).split())


def remove_special_chars(s):
    return ' '.join(''.join(i for i in s if i not in "\/:*?<>|").split()).replace('...', '…').rstrip('.')


def clean_list(l):
    # l = [' '.join(x).split() for x in l]   not needed because already ran
    n = 0
    while True:
        if all([x.startswith(' '.join(l[0].split()[:n])) for x in l]):
            n += 1
        else:
            return [' '.join(x.split()[n-1:]).capitalize() for x in l]


def search_mangas(q):
    data = requests.get('https://manganelo.com/search/story/'+format_for_url(q)).text
    chapters = bs(data, features='lxml').find('div', class_="panel-search-story").find_all('div', class_='search-story-item')
    mangas = []
    for chap in chapters:
        title = chap.find('a', class_="a-h text-nowrap item-title")['title'].strip()
        link = chap.find('a', class_="a-h text-nowrap item-title")['href'].strip()
        author = chap.find('span', class_="text-nowrap item-author").text.strip()
        updated = chap.find_all('span', class_="text-nowrap item-time")[0].text.replace('Updated :', '').strip()
        views = chap.find_all('span', class_="text-nowrap item-time")[1].text.replace('View :', '').strip()

        mangas.append({'title': title, 'link': link, 'author': author, 'updated': updated, 'views': views})
    return mangas



def download_images(url, path):
    global message
    old_msg = message
    message = old_msg + f' - Extracting info'
    data = requests.get(url).text
    images = bs(data, features='lxml').find('div', class_='container-chapter-reader').find_all('img')
    images = [x['src'] for x in images]
    reqs = []
    for img in images:
        reqs.append(grequests.get(img, headers={'Accept': 'image/webp,*/*', 'Referer': 'https://manganelo.com/'}, stream=True))

    message = old_msg + f' - Extracting image contents ({len(reqs)} files)'
    elapsed = time.time()
    resps = grequests.map(reqs, size=len(reqs))
    message = old_msg + f' - Done ({str(round(time.time()-elapsed, 3)).ljust(5, "0")}s) - Saving...'
    num = 1
    for r in resps:
        r.raise_for_status()
        with open(os.path.join(path, f'{str(num).rjust(3, "0")}{os.path.splitext(img)[-1]}'), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        num+=1


def get_chapters(url, main_path):
    global ticks, message, total_ticks, eta
    data = requests.get(url).text
    print('Downloading to ' + main_path)
    if not os.path.exists(main_path): os.mkdir(main_path)
    chapters = [[x['title'].strip(), x['href'].strip()] for x in bs(data, features='lxml')
                .find('div', class_='panel-story-chapter-list')
                .find_all('a', class_='chapter-name text-nowrap')
            ][::-1]
    chapters = list(zip(clean_list([i[0] for i in chapters]), [i[1] for i in chapters]))

    # eta stuff
    ticks = 0
    total_ticks = len(chapters)
    message = ''
    eta = ETA(total_ticks)

    t = Thread(target=eta_loop)
    t.daemon = True
    t.start()
    ticks = 0; message = ''


    for num, url in enumerate(chapters):
        ticks = num; message = f'Downloading {num+1}/{total_ticks}'
        folder_path = os.path.join(main_path, f'{str(num+1).rjust(4, "0")} - {remove_special_chars(url[0])}')
        if not os.path.exists(folder_path): os.mkdir(folder_path)
        download_images(url[1], folder_path)
    
    ticks = total_ticks
    time.sleep(0.2)


ticks, total_ticks, message, eta = None, None, None, None

if __name__ == '__main__':
    import inquirer
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='Mass downloads manga from manganelo.com')
    parser.add_argument('--path', '-p', type=str, default=None, help="Path to download manga")
    parser.add_argument('--name', '-n', type=str, default=None, help="Name of manga to search")
    parser.add_argument('--title', '-t', action="store_true", default=False, help="Shows title (hidden by default when ran through command line)")
    parser.add_argument('--link', '-l', type=str, default=None, help="Link to manga")
    args = parser.parse_args()

    if len(sys.argv) == 1 or args.title:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(r'''   __  ___                        ___  __ 
  /  |/  /__ ____  ___ ____ _____/ _ \/ / 
 / /|_/ / _ `/ _ \/ _ `/ _ `/___/ // / /__
/_/  /_/\_,_/_//_/\_, /\_,_/   /____/____/
                /___/                    
        ''')
    
    
    if args.link:
        if args.path:
            path = args.path
        else:
            data = requests.get(args.link).text
            title = bs(data, features='lxml').find('div', class_='story-info-right').find('h1').text.strip()
            path = os.path.join(os.getcwd(), remove_special_chars(title))
        get_chapters(args.link, path)
    else:
        if args.name:
            name = args.name
        else:
            name = input(f'[{Fore.GREEN}?{Fore.RESET}] Manga name: ')
        searched_mangas = search_mangas(name)
        choices_ = []
        for i in searched_mangas:
            choices_.append(f"{i['title']} | {i['views'].replace(' - ', ' ')} views")
        inp = choices_.index(inquirer.prompt([inquirer.List('_', message='Choose a manga', choices=choices_)])['_'])

        if args.path:
            path = args.path
        else:
            path = os.path.join(os.getcwd(), remove_special_chars(searched_mangas[inp]['title']))
        get_chapters(searched_mangas[inp]['link'], path)

    if len(sys.argv) == 1: input()