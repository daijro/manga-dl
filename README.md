# Manga-DL

Manganelo scraper


# Installation

Run this command in a terminal:

```
pip3 install -r requirements.txt
```


# Usage

By running the file, you will be prompted to enter a manga name and to select an option

### Command line arguments:


##### Options

```
$ manga-dl.py -h
usage: manga-dl.py [-h] [--path PATH] [--name NAME] [--title] [--link LINK]

Mass downloads manga from manganelo.com

optional arguments:
  -h, --help            show this help message and exit
  --path PATH, -p PATH  Path to download manga
  --name NAME, -n NAME  Name of manga to search
  --title, -t           Shows title (hidden by default when ran through command line)
  --link LINK, -l LINK  Link to manga
```


##### Searching a name


```
$ manga-dl.py --name "one piece"
[?] Choose a manga: One Piece | 122,317,270 views
 > One Piece | 122,317,270 views
   One Piece - Digital Colored Comics | 4,019,942 views
   Kimi no Kakera | 163,342 views
   Doujin Sakka Collection - himegoto | 117,749 views
```

### In action

![screen recording](https://user-images.githubusercontent.com/72637910/119973575-4553cd00-bf79-11eb-90eb-ab6debd13777.gif)
