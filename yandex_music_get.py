import eyed3
import urllib.request
import configparser
import os

from urllib.parse import urlparse
from pathlib import Path
from eyed3.core import AudioFile, Tag
from yandex_music import Artist, Client, Track, TracksList, Playlist, Album



def compile_artists(artists: list[Artist]) -> str:
    """Перечислить имена артистов через запятую в строке.
    """
    overall = ''
    for artist in artists:
        overall += f'{artist.name}, '
    return overall[:-2]


def setup_track_metadata(track: Track, mp3_path: str, cover_path: str, remove_cover = True):
    """Установить метаданные .mp3-файла: альбом, исполнитель, название, обложка.
    @param track Трек, из которого берется основная информация
    @param mp3_path Путь к .mp3-файлу
    @param cover_path Путь к .png-обложке
    @param remove_cover Стоит ли удалять .png-обложку. Если False, вызывающий сам ее удалит
    """
    audiofile = eyed3.load(mp3_path)
    audiofile.initTag(version=(2, 3, 0))
    audiofile.tag.artist = compile_artists(track.artists)
    audiofile.tag.album = track.albums[0].title
    audiofile.tag.album_artist = compile_artists(track.albums[0].artists)
    audiofile.tag.title = track.title

    with open(cover_path, "rb") as image_file:
        imagedata = image_file.read()
    audiofile.tag.images.set(3, imagedata, "image/png", u"cover")
    audiofile.tag.save()
    if remove_cover:
        os.remove(cover_path)

def download_lyrics(track: Track, path = './'):
    """Если у трека есть синхронизированный текст, записать его в .lrc-файл
    """
    if track.lyrics_info.has_available_sync_lyrics:
        with open( f'{path}{compile_artists(track.artists)} - {track.title}.lrc', 'w') as file:
            file.write(track.get_lyrics('LRC').fetch_lyrics())

def download_track(track : Track, path = './', album_cover = None):
    """Скачать трек (mp3), обложку (png, удалится после вызова) и текст (lrc), записать метаданные
    """
    if path[-1] != '/':
        path += '/'

    artists = compile_artists(track.artists)
    mp3_path = f'{path}{artists} - {track.title}.mp3'
    cover_path = f'{path}{artists} - {track.title}.cover.png'

    track.download(mp3_path)
    print(f'{artists} - {track.title}.mp3 ✅')

    if album_cover is None:
        track.download_cover(cover_path)
    else:
        cover_path = album_cover

    print(f'    обложка ✅')
    setup_track_metadata(track, mp3_path, cover_path, album_cover is None)
    print(f'    метаданные ✅')
    # download_lyrics(track, path)


def download_playlist(playlist: Playlist, path = './'):
    """Скачать плейлист в path/{playlist.title}
    """
    print(f"Название: {playlist.title}, ID: {playlist.kind}, Количество треков: {playlist.track_count}")
    print(f"Всего треков: {playlist.track_count}")

    if path[-1] != '/':
        path += '/'
    path += playlist.title

    for track in playlist.fetch_tracks():
        print(f'  {track.track.artists[0].name} - {track.track.title}')
        download_track(track.track, path)


def download_album(album: Album, path = './'):
    """Скачать альбом в path/{album.title}. Предварительно скачивает обложку,
    чтобы download_track не делал это для каждого трека
    """
    tracks = []
    for i, volume in enumerate(album.volumes):
        if len(album.volumes) > 1:
            tracks.append(f'💿 Диск {i + 1}')
        tracks += volume

    if path[-1] != '/':
        path += '/'
    path += album.title

    p = Path(path)
    if not p.exists():
        os.mkdir(path)

    cover_path = f'{path}/{album.title}.png'
    album.download_cover(cover_path)
    for track in tracks:
        download_track(track, path, cover_path)
    os.remove(cover_path)


def download_by_url(url_string: str, path = './'):
    """Скачать трек или альбом в зависимости от типа ссылки.
    """
    parsed_url = urlparse(url_string)
    parameters = parsed_url.path.split('/')

    track_id = None
    album_id = None
    for i in range(len(parameters)):
        if parameters[i] == 'album':
            album_id = parameters[i + 1]
        if parameters[i] == 'track':
            track_id = parameters[i + 1]
            break

    if track_id is None:
        if album_id is not None:
            download_album(client.albums_with_tracks(album_id), path)
    else:
        download_track(client.tracks(track_id)[0], path)

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('data.ini')
    client = Client(config['yandex']['access_token']).init()
