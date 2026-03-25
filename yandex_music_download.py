import configparser
import datetime
import os

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button, Label, Checkbox
from textual.containers import HorizontalGroup, VerticalScroll, Grid
from textual_fspicker import SelectDirectory
from textual.screen import ModalScreen
from pathlib import Path
from pygame import mixer

from yandex_music import Client, Track
from yandex_music_get import compile_artists, download_track


class Player:
    def __init__(self):
        mixer.init()
        self.path = None
        self.max_tracks = 5
        self.i = 0
        self.tracklist = []
        temp_path = Path('./temp')
        for item in temp_path.iterdir():
            self.tracklist.append(f'./temp/{item.name}')
            self.i += 1

    def is_cached(self, mp3_path):
        return mp3_path in self.tracklist
    
    def play(self, mp3_path):
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

    def is_playing(self, mp3_path):
        return mixer.music.get_busy() and self.path == mp3_path



class MessageBox(ModalScreen):
    def __init__(self, message: str, title: str = "Сообщение"):
        super().__init__()
        self.message = message
        self.title = title

    def compose(self):
        yield Grid(
            Label(self.title, id="title"),
            Label(self.message, id="message"),
            id="dialog"
        )

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



class Download_folder(HorizontalGroup):
    def __init__(self, path: str, **kwargs):
        super().__init__(**kwargs)
        self.path = path

    def compose(self) -> ComposeResult:
        yield Label('Download folder:', id='download_folder_label')
        self.path_label = Label(self.path, id='download_path')
        yield self.path_label
        yield Button(label='📁...', flat=True)

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed):
        """Открыть диалог выбора папки"""
        self.app.push_screen(
            SelectDirectory(
                location=self.path,
                title="Select Download Folder"
            ),
            callback=self.update_folder
        )

    def update_folder(self, selected_path):
        """Обновить путь после выбора"""
        if selected_path:
            self.path = str(selected_path)
            self.path_label.update(self.path)



class Track_row(HorizontalGroup):
    def __init__(self, track: Track, player: Player, download_folder: Download_folder, **kwargs):
            super().__init__(**kwargs)
            self.view = Track_view(compile_artists(track.artists), track.title, track.duration_ms)
            self.track = track
            self.download_folder = download_folder
            self.player = player

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
            self.message_box = MessageBox(f'downloaded at {self.download_folder.path}{self.view.name()}.mp3', self.view.name())
            self.app.push_screen(self.message_box)
            download_track(track=self.track, path=self.download_folder.path)
            self.set_timer(1, lambda: self.app.pop_screen())
        else:
            path = self.temp_path()
            if not self.player.is_cached(path):
                self.track.download(path)
            self.player.play(path)

    def close_message_box(self):
        """Закрыть окно сообщения извне"""
        if self.message_box and self.message_box.is_attached:
            self.message_box.dismiss()



class Navigation(HorizontalGroup):  
    def __init__(self, track_list: list[Track], set_page_lambda,  **kwargs):
        super().__init__(**kwargs)
        self.tracks_size = len(track_list)
        self.max_index = self.tracks_size // 10  + 1
        self.index = 0
        self.set_page_lambda = set_page_lambda

    def index_string(self) -> str:
        return f'{self.index} / {self.max_index}'

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



class Tracklist_app(App):
    def __init__(self, path: str, tracks: list[Track], player: Player, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.tracks = tracks
        self.player = player

    def tracklist(self, page: int) -> list:
        tracks = []
        for i in range(page * 10, (page * 10) + 10):
            tracks.append(Track_row(self.tracks[i], self.player, self.download_folder))
        return tracks

    def compose(self) -> ComposeResult:
        self.download_folder = Download_folder(self.path)
        self.scroll = VerticalScroll(self.download_folder, *self.tracklist(0), Navigation(self.tracks, lambda page: self.set_page(page)))
        yield Header()
        yield Footer()
        yield self.scroll

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
            ("q", "quit", "Quit"),
            ("t", "toggle_dark", "Toggle dark mode"),
        ]
    
    def action_quit(self) -> None:
        self.exit()

    def action_toggle_dard(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )



if __name__ == '__main__':
    print("Fetching music...")
    config = configparser.ConfigParser()
    config.read('data.ini')
    client = Client(config['yandex']['access_token']).init()
    # download_track(client.users_likes_tracks().fetch_tracks()[4], '/mnt/c/Users/atochilin/Desktop/msc')    

    temp_path = Path('./temp')
    if not temp_path.exists():
        os.mkdir(temp_path)

    player = Player()

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
    app = Tracklist_app('/home/greggot/Музыка/', client.users_likes_tracks().fetch_tracks(), player)
    app.run()
