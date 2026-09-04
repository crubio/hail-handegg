from dataclasses import dataclass, field


@dataclass
class DraftSession:
    draft_position: int
    num_teams: int
    # {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DST": 1, "BN": 6, "IR": 1}
    roster_slots: dict
    draft_style: str = "snake"

    # Each entry: {"player_id", "name", "position", "team", "score"}
    my_roster: list = field(default_factory=list)
    # Player IDs drafted by other teams
    other_drafted: set = field(default_factory=set)

    def __post_init__(self) -> None:
        if not (1 <= self.draft_position <= self.num_teams):
            raise ValueError(
                f"draft_position {self.draft_position} out of range "
                f"[1, {self.num_teams}] — check config/league.yaml"
            )

    def add_pick(self, player: dict) -> None:
        if not any(p["player_id"] == player["player_id"] for p in self.my_roster):
            self.my_roster.append(player)

    def mark_drafted(self, player_id: str) -> None:
        self.other_drafted.add(player_id)

    def undo_last_pick(self, player_id: str) -> dict | None:
        """Remove and return the roster entry matching player_id, or None if not found."""
        for i, p in enumerate(self.my_roster):
            if p["player_id"] == player_id:
                return self.my_roster.pop(i)
        return None

    def undo_mark_drafted(self, player_id: str) -> None:
        self.other_drafted.discard(player_id)

    def my_player_ids(self) -> set:
        return {p["player_id"] for p in self.my_roster}

    def all_drafted_ids(self) -> set:
        return self.my_player_ids() | self.other_drafted

    def roster_needs(self) -> dict[str, int]:
        """Remaining open slots per slot label.

        FLEX is filled by overflow RB/WR/TE beyond their own slot counts.
        BN absorbs everyone else after starters + FLEX are filled.
        IR is left as-is (not automatically filled).
        """
        pos_counts: dict[str, int] = {}
        for p in self.my_roster:
            pos = p["position"]
            pos_counts[pos] = pos_counts.get(pos, 0) + 1

        starter_positions = {k for k in self.roster_slots if k not in ("BN", "IR", "FLEX")}

        # Overflow = picks beyond a position's starter slots
        overflow = sum(
            max(0, pos_counts.get(pos, 0) - (self.roster_slots.get(pos) or 0))
            for pos in ("RB", "WR", "TE")
        )

        total_starter_slots = sum(
            (self.roster_slots.get(p) or 0) for p in starter_positions
        ) + (self.roster_slots.get("FLEX") or 0)

        bench_filled = max(0, len(self.my_roster) - total_starter_slots)

        needs = {}
        for slot, count in self.roster_slots.items():
            count = count or 0
            if slot == "FLEX":
                needs[slot] = max(0, count - overflow)
            elif slot == "BN":
                needs[slot] = max(0, count - bench_filled)
            elif slot == "IR":
                needs[slot] = count  # not auto-filled
            else:
                needs[slot] = max(0, count - pos_counts.get(slot, 0))

        return needs

    def current_round(self) -> int:
        return len(self.my_roster) + 1

    def next_pick_number(self) -> int:
        """Overall pick number for the user's next turn in a snake draft."""
        rnd = self.current_round()
        if self.draft_style != "snake":
            raise NotImplementedError("Only snake draft supported")
        if rnd % 2 == 1:
            return (rnd - 1) * self.num_teams + self.draft_position
        else:
            return rnd * self.num_teams - self.draft_position + 1
