from textual.screen import Screen
from textual.widgets import DataTable, Input, Footer, Header


class DraftBoardScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self):
        yield Header()
        yield DataTable(id="player-table")
        yield Input(placeholder="Enter picked player name...", id="pick-input")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#player-table", DataTable)
        table.add_columns("Rank", "Player", "Pos", "Team", "Score", "ADP", "Proj Pts")
        # TODO: populate from scored dataframe

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # TODO: record pick, update board
        pass
