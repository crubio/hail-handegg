from dataclasses import dataclass, field


@dataclass
class DraftSession:
    draft_position: int
    num_teams: int
    roster_slots: dict  # e.g. {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DST": 1, "BN": 6, "IR": 1}
    draft_style: str = "snake"

    my_roster: list = field(default_factory=list)  # player ids the user has drafted

    def add_pick(self, player_id: str) -> None:
        if player_id not in self.my_roster:
            self.my_roster.append(player_id)

    def roster_needs(self) -> dict:
        # TODO: implement — returns remaining open slots by position
        raise NotImplementedError

    def next_pick_number(self, current_round: int) -> int:
        """Returns the overall pick number for the user's next turn in a snake draft."""
        if self.draft_style != "snake":
            raise NotImplementedError("Only snake draft supported")
        if current_round % 2 == 1:
            return (current_round - 1) * self.num_teams + self.draft_position
        else:
            return current_round * self.num_teams - self.draft_position + 1
