from textual.app import App

from tui.screens.draft_board import DraftBoardScreen


class HailHandeggApp(App):
    TITLE = "hail-handegg"

    def on_mount(self) -> None:
        self.push_screen(DraftBoardScreen())


def run() -> None:
    HailHandeggApp().run()
