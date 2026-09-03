from dataclasses import dataclass, field


@dataclass
class DraftSession:
    draft_position: int
    num_teams: int
    roster_slots: dict  # e.g. {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DST": 1}
    draft_style: str = "snake"

    drafted: list = field(default_factory=list)       # all picked player ids
    my_roster: list = field(default_factory=list)     # my picked player ids

    def record_pick(self, player_id: str, team_pick: int) -> None:
        # TODO: implement
        raise NotImplementedError

    def available_players(self, all_players: list) -> list:
        # TODO: implement — returns all_players minus drafted
        raise NotImplementedError

    def roster_needs(self) -> dict:
        # TODO: implement — returns remaining open slots by position
        raise NotImplementedError
