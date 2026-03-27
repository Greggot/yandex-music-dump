import configparser
import datetime
import os
from typing import Callable, final, override
from urllib.parse import urlparse

import pyperclip
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button, Label
from textual.containers import HorizontalGroup, HorizontalScroll, VerticalScroll, Grid
from textual_fspicker import SelectDirectory
from textual.screen import ModalScreen
from textual.events import AppFocus
from pathlib import Path
from pygame import mixer

from yandex_music import Album, Client, Track
from yandex_music_get import compile_artists, download_album, download_track


@final
class Player:
    def __init__(self):
        mixer.init()
        self.path = None
        self.max_tracks = 5
        self.i = 0
        self.tracklist: list[str] = []
        temp_path = Path('./temp')
        for item in temp_path.iterdir():
            self.tracklist.append(f'./temp/{item.name}')
            self.i += 1

    def is_cached(self, mp3_path: str):
        return mp3_path in self.tracklist
    
    def play(self, mp3_path: str):
        if self.path == mp3_path:
            mixer.music.stop()
            self.path = None
        else:
            if mp3_path not in self.tracklist:
                if len(self.tracklist) >= self.max_tracks:
                    if self.i >= self.max_tracks:
                        self.i = 0
                    os.remove(self.tracklist[self.i])
                    self.tracklist[self.i] = mp3_path
                    self.i += 1
                else:
                    self.tracklist.append(mp3_path)
                    self.i += 1

            self.path = mp3_path
            mixer.music.load(self.path)
            mixer.music.play()

    def stop(self):
        mixer.music.stop()

    def is_playing(self, mp3_path: str):
        return mixer.music.get_busy() and self.path == mp3_path



@final
class MessageBox(ModalScreen[None]):
    def __init__(self, message: str, header: str = "Сообщение"):
        super().__init__()
        self.message = message
        self.header = header

    @override
    def compose(self):
        yield Grid(
            Label(self.header, id="title"),
            Label(self.message, id="message"),
            id="dialog"
        )

@final
class YesNoBox(ModalScreen[bool]):
    def __init__(self, header: str = 'Да-Нет', message: str = "Сообщение"):
        super().__init__()
        self.header = header
        self.message = message
        self.yes_button = Button(label='yes', id='modal_yes', variant='success', flat=True)
        self.no_button = Button(label='no', id='modal_no', variant='error', flat=True)

    @override
    def compose(self):
        yield VerticalScroll(
            Label(self.header, id="title"),
            Label(self.message, id="message"),
            HorizontalScroll(
                self.yes_button,
                self.no_button,
                id='yes_no_button_div'
            ),
            id="dialog"
        )

    @on(Button.Pressed)
    def select_option(self, event: Button.Pressed) -> None:
        if event.button == self.yes_button:
            self.dismiss(True)
        else:
            self.dismiss(False)

@final
class Track_view:
    def __init__(self, artist: str, track: str, duration_ms: int):
        self.artist = artist
        self.track = track
        duration = datetime.datetime.fromtimestamp(duration_ms / 1000.0)
        self.duration_min = str(duration.minute).zfill(2)
        self.duration_sec = str(duration.second).zfill(2)

    def duration(self) -> str:
        return f'{self.duration_min}:{self.duration_sec}'
    
    def name(self) -> str:
        return f'{self.artist} - {self.track}'


@final
class Download_folder(HorizontalGroup):
    def __init__(self, path: str, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.path_label: Label

    @override
    def compose(self) -> ComposeResult:
        yield Label('Download folder:', id='download_folder_label')
        self.path_label = Label(self.path, id='download_path')
        yield self.path_label
        yield Button(label='📁...', flat=True, id='download_picker')

    @on(Button.Pressed)
    def on_button_pressed(self, _: Button.Pressed):
        """Открыть диалог выбора папки"""
        self.app.push_screen(
            SelectDirectory(
                location=self.path,
                title="Select Download Folder"
            ),
            callback=self.update_folder
        )

    def update_folder(self, selected_path: Path | None):
        """Обновить путь после выбора"""
        if selected_path:
            self.path = str(selected_path)
            self.path_label.update(self.path)



@final
class Clipboard_download(HorizontalGroup):
    def __init__(self, track_name: str, **kwargs):
        super().__init__(**kwargs)
        self.track_name = track_name 
        self.path_label: Label

    @override
    def compose(self) -> ComposeResult:
        yield Label(f'Download: {self.track_name}? ', id='clipboard_name')
        yield Button(label='✅', flat=True, id='clipboard_yes')
        yield Button(label='❌', flat=True, id='clipboard_no')



@final
class Track_row(HorizontalGroup):
    def __init__(self, track: Track, player: Player, download_folder: Download_folder, **kwargs):
            super().__init__(**kwargs)
            self.view = Track_view(compile_artists(track.artists), track.title or 'Unknown', track.duration_ms or 0)
            self.track = track
            self.download_folder = download_folder
            self.player = player
            self.play_button: Button
            self.download_button: Button

    @override
    def compose(self) -> ComposeResult:
        icon = '⏸'
        if self.player.is_playing(self.temp_path()): 
            icon = '▶'
        self.play_button = Button(label=icon, id='play_button', variant='primary', flat=True)
        self.download_button = Button(label='⬇', id='download_button', variant='success', flat=True)
        yield Label(self.view.name(), id='track_name')
        yield Label(self.view.duration(), id='track_length')
        yield self.play_button
        yield self.download_button

    def temp_path(self) -> str:
        return f'./temp/{compile_artists(self.track.artists)} - {self.track.title}.mp3'

    @on(Button.Pressed)
    def show_dialog(self, event: Button.Pressed):
        if event.button == self.download_button:
            message_box = MessageBox(f'downloaded at {self.download_folder.path}{self.view.name()}.mp3', self.view.name())
            self.app.push_screen(message_box)
            download_track(track=self.track, path=self.download_folder.path)
            self.set_timer(1, lambda: self.app.pop_screen())
        else:
            path = self.temp_path()
            if not self.player.is_cached(path):
                self.track.download(path)
            self.player.play(path)



@final
class Navigation(HorizontalGroup):  
    def __init__(self, track_list: list[Track], set_page_lambda: Callable[[int], None],  **kwargs):
        super().__init__(**kwargs)
        self.tracks_size = len(track_list)
        self.max_index = self.tracks_size // 10  + 1
        self.index = 0
        self.set_page_lambda = set_page_lambda
        self.index_label: Label
        self.prev_button: Button
        self.next_button: Button

    def index_string(self) -> str:
        return f'{self.index} / {self.max_index}'

    @override
    def compose(self) -> ComposeResult:
        self.index_label = Label(self.index_string(), id='navigation_index')
        self.prev_button = Button(label='⬅', flat=True, disabled=True, id='navigation_prev_button')
        self.next_button =  Button(label='➡', flat=True, id='navigation_next_button')
        yield self.prev_button
        yield self.index_label
        yield self.next_button

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed):
        if event.button == self.next_button:
            if self.index < self.max_index:
                self.index = self.index + 1
                self.index_label.update(self.index_string())
            if self.index == self.max_index:
                self.next_button.disabled = True
            if self.index == 1:
                self.prev_button.disabled = False
        else:
            if self.index > 0:
                self.index = self.index - 1
                self.index_label.update(self.index_string())
            if self.index == 0:
                self.prev_button.disabled = True
            if self.index == self.max_index - 1:
                self.next_button.disabled = False
        self.set_page_lambda(self.index)



@final
class Clipboard_download:
    def __init__(self, client: Client, download_folder: Download_folder, app: App[None]):
        self.app = app
        self.clipboard_track: Track | None = None
        self.clipboard_album: Album | None = None
        self.client = client
        self.download_folder = download_folder

    
    def download_track_from_clipboard(self, track_id: str):
        def download_from_clipboard(is_download: bool | None) -> None:
            if is_download and self.clipboard_track:
                download_track(track=self.clipboard_track, path=self.download_folder.path)

        tracks = self.client.tracks(track_id)
        if tracks and (self.clipboard_track is None or self.clipboard_track.id != track_id):
            self.clipboard_track = tracks[0]
            self.app.push_screen(YesNoBox('Ссылка из буфера обмена', 
                f'Скачать трек \"{compile_artists(self.clipboard_track.artists)} - {self.clipboard_track.title}\"'), download_from_clipboard)

    def download_album_from_clipboard(self, album_id: str):
        def download_from_clipboard(is_download: bool | None) -> None:
            if is_download and self.clipboard_album:
                download_album(album=self.clipboard_album, path=self.download_folder.path)

        if self.clipboard_album is None or str(self.clipboard_album.id) != album_id:
            self.clipboard_album = client.albums_with_tracks(album_id)
            if self.clipboard_album:
                self.app.push_screen(YesNoBox('Ссылка из буфера обмена', 
                    f'Скачать альбом \"{self.clipboard_album.title} ?'), download_from_clipboard)

    def on_focus(self):
        parsed_url = urlparse(pyperclip.paste())
        if parsed_url.hostname is None:
            return
        if parsed_url.hostname != 'music.yandex.ru':
            return
        parameters = parsed_url.path.split('/')
        track_id: str | None = None
        album_id: str | None = None
        for i in range(len(parameters)):
            if parameters[i] == 'album':
                album_id = parameters[i + 1]
            if parameters[i] == 'track':
                track_id = parameters[i + 1]
                break

        if track_id is not None:
            self.download_track_from_clipboard(track_id)

        elif album_id is not None:
            self.download_album_from_clipboard(album_id)
                

@final
class Tracklist_app(App[None]):
    def __init__(self, path: str, client: Client, tracks: list[Track], player: Player, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.client = client
        self.tracks = tracks
        self.player = player
        self.scroll: VerticalScroll
        self.download_folder = Download_folder(self.path)
        self.clipboard_download = Clipboard_download(client, self.download_folder, self)
    def tracklist(self, page: int) -> list[Track_row]:
        tracks: list[Track_row] = []
        for i in range(page * 10, (page * 10) + 10):
            tracks.append(Track_row(self.tracks[i], self.player, self.download_folder))
        return tracks

    @override
    def compose(self) -> ComposeResult:
        self.scroll = VerticalScroll(
            self.download_folder, 
            *self.tracklist(0), 
            Navigation(self.tracks, lambda page: self.set_page(page)))
        yield Header()
        yield Footer()
        yield self.scroll
    @on(AppFocus)
    def on_app_focus(self, _: AppFocus) -> None:
        self.clipboard_download.on_focus()


    def set_page(self, page: int):
        """Обновить отображение при смене страницы"""
        children = list(self.scroll.children)
        for child in children:
            if not isinstance(child, (Download_folder, Navigation)):
                child.remove()
        
        insert_index = 1
        for track in self.tracklist(page):
            self.scroll.mount(track, before=insert_index)
            insert_index += 1


    CSS_PATH = "ymd.tcss"
    BINDINGS = [
            ("q", "onquit", "Quit"),
            ("t", "toggle_dark", "Toggle dark mode"),
        ]
    
    def action_onquit(self) -> None:
        self.exit()

    def action_toggle_dard(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )



def music_folder() -> str:
    home_folder = os.environ['HOME']
    for music_folder in ['Музыка', 'Music']:
        path = Path(f'{home_folder}/{music_folder}')
        if path.exists():
            return str(path)
    return home_folder



if __name__ == '__main__':
    print("Fetching music...")
    config = configparser.ConfigParser()
    config.read('data.ini')
    client = Client(config['yandex']['access_token']).init()
    # download_track(client.users_likes_tracks().fetch_tracks()[4], '/mnt/c/Users/atochilin/Desktop/msc')    

    temp_path = Path('./temp')
    if not temp_path.exists():
        os.mkdir(temp_path)


    # tracks = []
    # playlist = client.users_playlists_list()[0]
    # playlist_tracks = playlist.fetch_tracks()
    # for i, track in enumerate(playlist_tracks, 1):
    #     tracks.append(track.track)


    # with open("like.json", "w") as file:
        # file.write(str(client.users_likes_playlists()[0]))

    # for like in client.users_likes_playlists():
    #     if like.type == 'playlist':
    #         print(f'Owner: {like.playlist.owner.name}')
    #         print(f'Title: {like.playlist.title}')
    #         if like.playlist.owner.name == 'potom':
    #             print('    FOUND')
    #             for i, track in enumerate(like.playlist.fetch_tracks(), 1):
    #                 tracks.append(track.track)


    # app = Tracklist_app('/home/greggot/Музыка/', tracks, player)
    track_list = client.users_likes_tracks()
    if track_list:
        app = Tracklist_app(music_folder(), client, track_list.fetch_tracks(), Player())
        app.run()
