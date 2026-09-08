from __future__ import annotations

import unittest
from copy import deepcopy

from loltee_scraper.build_teamplay import (
    build_teamplay_champion, build_teamplay_dataset, teamplay_ban_sort_key,
    TEAMPLAY_BAN_SCORE_FORMULA, TEAMPLAY_BAN_SCORE_METHOD,
)
from loltee_scraper.oracle_teamplay import OracleRoleStats, OracleChampionStats, OracleTeamplaySnapshot


def champion(name="Alpha", ban=1.0, pick=0.5, rank=3, pbi=0):
    return build_teamplay_champion(
        {"name": name, "filtered_rank": rank, "pbi": pbi}, lane="middle", lane_count=11,
        role_stats=OracleRoleStats(5, pick, 2, 40, 10, 1, ban),
        champion_stats=OracleChampionStats(5, ban, 1, 5),
        lane_max_role_pick_rate=1, lane_max_role_adjusted_ban_rate=1,
    )


def dataset(solo=None, roles=None, stats=None):
    return build_teamplay_dataset(
        solo_dataset={"meta": {"warnings": []}, "data": solo or {}},
        pro_snapshot=OracleTeamplaySnapshot(
            [], [], 10, roles or {}, stats or {},
            {"middle": 1, "top": 1}, {"middle": 1, "top": 1}, 1, False, [], 0, 0,
        ), region="na", tier="gold", window="7d",
    )


class TeamplayBanTests(unittest.TestCase):
    def test_exact_formula_and_pick_scores_unchanged(self):
        c = champion()
        self.assertEqual(c["teamplay_ban_score"], 0.88)
        self.assertEqual(c["solo_strength_score"], 0.8)
        self.assertEqual(c["pro_score"], 0.625)
        self.assertEqual(c["flex_clash_score"], 0.6425)

    def test_ban_evidence_dominates(self):
        banned = champion(ban=1, pick=0.1, rank=11)
        picked = champion(ban=0.1, pick=1, rank=1)
        self.assertLess(teamplay_ban_sort_key(banned), teamplay_ban_sort_key(picked))

    def test_practical_signal(self):
        practical = champion(ban=0.5, pick=1, rank=1)
        weaker = champion(ban=0.6, pick=0.1, rank=11)
        self.assertLess(teamplay_ban_sort_key(practical), teamplay_ban_sort_key(weaker))

    def test_no_pbi_in_score_or_ties(self):
        a, b = champion(pbi=-1000000), champion(pbi=1000000)
        self.assertEqual(a["teamplay_ban_score"], b["teamplay_ban_score"])
        self.assertEqual(teamplay_ban_sort_key(a), teamplay_ban_sort_key(b))

    def test_each_tie_breaker_in_order(self):
        fields = ["teamplay_ban_score", "role_adjusted_ban_rate", "pro_role_pick_rate",
                  "solo_strength_score", "teamplay_rank", "name"]
        base = dict(zip(fields, [0.5, 0.5, 0.5, 0.5, 2, "Bravo"]))
        for i, field in enumerate(fields):
            with self.subTest(field=field):
                preferred = dict(base)
                preferred[field] = "Alpha" if field == "name" else (1 if field == "teamplay_rank" else 0.6)
                # Later criteria favor the other champion, so precedence is tested too.
                for later in fields[i + 1:]:
                    preferred[later] = "Zulu" if later == "name" else (99 if later == "teamplay_rank" else 0)
                self.assertLess(teamplay_ban_sort_key(preferred), teamplay_ban_sort_key(base))

    def test_lane_specificity_eligibility_and_pick_rank(self):
        pool = [{"name": n, "filtered_rank": i + 1, "pbi": 10000 - i}
                for i, n in enumerate(["Alpha", "Bravo", "Excluded", "NoPicks", "Absent"])]
        roles = {}
        for lane, alpha_ban, bravo_ban in [("middle", 1, 0), ("top", 0.1, 0.9)]:
            roles[("alpha", lane)] = OracleRoleStats(5, 0.2, 2, 40, 10, 0.5, alpha_ban)
            roles[("bravo", lane)] = OracleRoleStats(10, 1, 5, 50, 10, 0.5, bravo_ban)
            roles[("excluded", lane)] = OracleRoleStats(1, 1, 1, 100, 10, 1, 1)
        stats = {"alpha": OracleChampionStats(5, 1, 2, 10),
                 "bravo": OracleChampionStats(0, 0, 2, 20),
                 "excluded": OracleChampionStats(3, 1, 1, 1),
                 "nopicks": OracleChampionStats(100, 1, 0, 0)}
        solo = {"middle": pool, "top": deepcopy(pool)}
        original = deepcopy(solo)
        result = dataset(solo, roles, stats)
        self.assertEqual(solo, original)
        for lane in solo:
            rows = result["data"][lane]
            self.assertEqual([c["name"] for c in rows], ["Bravo", "Alpha"])
            self.assertEqual([c["teamplay_rank"] for c in rows], [1, 2])
            self.assertEqual(sorted(c["teamplay_ban_rank"] for c in rows), [1, 2])
        self.assertEqual([c["teamplay_ban_rank"] for c in result["data"]["middle"]], [2, 1])
        self.assertEqual([c["teamplay_ban_rank"] for c in result["data"]["top"]], [1, 2])
        self.assertEqual(result["meta"]["teamplay_ban_score_method"], TEAMPLAY_BAN_SCORE_METHOD)
        self.assertEqual(result["meta"]["teamplay_ban_score_formula"], TEAMPLAY_BAN_SCORE_FORMULA)
        self.assertEqual(result["data"]["jungle"], [])
        for row in pool:
            row["pbi"] *= -100
        repeated = dataset(solo, roles, stats)
        for lane in solo:
            self.assertEqual([(c["name"], c["teamplay_ban_rank"]) for c in result["data"][lane]],
                             [(c["name"], c["teamplay_ban_rank"]) for c in repeated["data"][lane]])

    def test_equal_scores_stable_under_input_reordering(self):
        pool = [{"name": n, "filtered_rank": 1} for n in ["Bravo", "Alpha"]]
        roles = {(n.lower(), "middle"): OracleRoleStats(5, 1, 2, 40, 10, 1, 0) for n in ["Alpha", "Bravo"]}
        first = dataset({"middle": pool}, roles)["data"]["middle"]
        second = dataset({"middle": list(reversed(pool))}, roles)["data"]["middle"]
        self.assertEqual(first, second)
        self.assertEqual([(c["name"], c["teamplay_ban_rank"]) for c in first], [("Alpha", 1), ("Bravo", 2)])


if __name__ == "__main__":
    unittest.main()
