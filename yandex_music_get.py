import configparser
import datetime
import os
from pathlib import Path
from urllib.parse import urlparse

import eyed3
from eyed3.core import Date
import pyperclip
from yandex_music import Album, Artist, Client, Playlist, Track


def compile_artists(artists: list[Artist]) -> str:
    """Перечислить имена артистов через запятую в строке.
    """
    overall = ''
    for artist in artists:
        overall += f'{artist.name}, '
    return overall[:-2]


def setup_track_metadata(track: Track, mp3_path: str, cover_path: str, remove_cover: bool = True):
    """Установить метаданные .mp3-файла: альбом, исполнитель, название, обложка.
    @param track Трек, из которого берется основная информация
    @param mp3_path Путь к .mp3-файлу
    @param cover_path Путь к .png-обложке
    @param remove_cover Стоит ли удалять .png-обложку. Если False, вызывающий сам ее удалит
    """
    audiofile = eyed3.load(mp3_path)
    if audiofile is None:
        return
    album = track.albums[0]
    audiofile.initTag(version=(2, 3, 0))
    audiofile.tag.artist = compile_artists(track.artists)
    audiofile.tag.album = album.title
    audiofile.tag.album_artist = compile_artists(album.artists)
    audiofile.tag.title = track.title
    audiofile.tag.genre = album.genre  # pyright: ignore[reportAttributeAccessIssue]
    audiofile.tag.recording_date = Date(album.year) # pyright: ignore[reportAttributeAccessIssue]
    if album.track_position:
        audiofile.tag.track_num = album.track_position.index

    with open(cover_path, "rb") as image_file:
        imagedata = image_file.read()
    audiofile.tag.images.set(3, imagedata, "image/png", u"cover") # pyright: ignore[reportAttributeAccessIssue]
    audiofile.tag.save() # pyright: ignore[reportAttributeAccessIssue]
    if remove_cover:
        os.remove(cover_path)

def download_lyrics(track: Track, path: str = './'):
    """Если у трека есть синхронизированный текст, записать его в .lrc-файл
    """
    if track.lyrics_info is None:
        return
    if track.lyrics_info.has_available_sync_lyrics:
        if lyrics:= track.get_lyrics('LRC'):
            with open( f'{path}{compile_artists(track.artists)} - {track.title}.lrc', 'w') as file:
                file.write(lyrics.fetch_lyrics())


def download_track(track : Track, path: str = './', lyrics: bool = True, album_cover: str | None = None):
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
        track.download_cover(cover_path, '400x400')
    else:
        cover_path = album_cover

    print(f'    обложка ✅')
    setup_track_metadata(track, mp3_path, cover_path, album_cover is None)
    print(f'    метаданные ✅')
    if lyrics:
        download_lyrics(track, path)


def download_playlist(playlist: Playlist, path: str = './'):
    """Скачать плейлист в path/{playlist.title}
    """
    print(f"Название: {playlist.title}, ID: {playlist.kind}, Количество треков: {playlist.track_count}")
    print(f"Всего треков: {playlist.track_count}")

    if path[-1] != '/':
        path += '/'
    path += playlist.title or ''

    for shorttrack in playlist.fetch_tracks():
        track = shorttrack.track
        if track is None:
            continue
        print(f'  {track.artists[0].name} - {track.title}')
        download_track(track=track, path=path)


def download_album(album: Album | None, path: str = './'):
    """Скачать альбом в path/{album.title}. Предварительно скачивает обложку,
    чтобы download_track не делал это для каждого трека
    """
    if album is None or album.volumes is None:
        return

    tracks: list[Track] = []
    for i, volume in enumerate(album.volumes):
        tracks += volume

    if path[-1] != '/':
        path += '/'
    path += album.title or ''

    p = Path(path)
    if not p.exists():
        os.mkdir(path)

    cover_path = f'{path}/{album.title}.png'
    album.download_cover(cover_path, '400x400')
    for track in tracks:
        download_track(track=track, path=path, album_cover=cover_path)
    os.remove(cover_path)


def download_by_url(client: Client, url_string: str, path: str = './'):
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
        tracks = client.tracks(track_id)
        if tracks:
            download_track(track=tracks[0], path=path)



def print_info(track: Track):
    print(f'{compile_artists(track.artists)} - {track.title}, {track.albums[0].year}')
    duration = datetime.datetime.fromtimestamp((track.duration_ms or 0) / 1000.0)
    print(f'  duration {str(duration.minute).zfill(2)}:{str(duration.second).zfill(2)} ')

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('data.ini')
    client = Client(config['yandex']['access_token']).init()
    # download_track(client.users_likes_tracks().fetch_tracks()[4], '/mnt/c/Users/atochilin/Desktop/msc')    
    # print_info(client.users_likes_tracks().fetch_tracks()[2])
    # with open("track.json", "w") as file:
        # file.write(str(client.users_likes_tracks().fetch_tracks()[2]))
