from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests


def _base_url_from_args() -> str:
    return os.environ.get("API_BASE", "http://localhost:8000/api/v1").rstrip("/")


def login(base: str, email: str, password: str) -> tuple[str, int]:
    url = f"{base}/auth/login"
    resp = requests.post(url, json={"email": email, "password": password}, timeout=15)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status_code") and body.get("status_code") != 200:
        raise RuntimeError(f"Login failed: {body}")
    data = body.get("data") or {}
    token = data.get("access_token")
    manager_id = data.get("manager_id")
    if not token:
        raise RuntimeError(f"No access_token in response: {body}")
    if manager_id is None:
        # Fallback to /auth/me
        me = requests.get(f"{base}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=15).json()
        manager_id = ((me or {}).get("data") or {}).get("manager_id")
    if manager_id is None:
        raise RuntimeError("Could not determine manager_id")
    return token, int(manager_id)


def list_players(base: str, page: int = 1, page_size: int = 100) -> list[dict[str, Any]]:
    url = f"{base}/players"
    resp = requests.get(
        url,
        params={"page": page, "page_size": page_size, "active_only": True},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data") or []
    return data


def pick_squad(all_players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Required quotas from ManagerService: {1:2, 2:5, 3:5, 4:3}
    required_by_position = {1: 2, 2: 5, 3: 5, 4: 3}
    per_team_cap = 3

    chosen: list[dict[str, Any]] = []
    team_counts: dict[int, int] = {}
    used_ids: set[int] = set()

    def can_take(p: dict[str, Any]) -> bool:
        pid = int(p["player_id"])  # type: ignore[index]
        if pid in used_ids:
            return False
        team_id = int(p["team_id"])  # type: ignore[index]
        if team_counts.get(team_id, 0) >= per_team_cap:
            return False
        return True

    # Group by position for easier selection
    pos_to_players: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: [], 4: []}
    for p in all_players:
        pos = int(p.get("position_id") or 0)
        if pos in pos_to_players:
            pos_to_players[pos].append(p)

    # Select per quota
    for pos, need in required_by_position.items():
        pool = pos_to_players.get(pos, [])
        for p in pool:
            if len([x for x in chosen if int(x["position_id"]) == pos]) >= need:
                break
            if can_take(p):
                chosen.append(p)
                used_ids.add(int(p["player_id"]))
                team_id = int(p["team_id"])  # type: ignore[index]
                team_counts[team_id] = team_counts.get(team_id, 0) + 1

    if len(chosen) != 15:
        # Try to top-up from any remaining players while respecting per-team cap and uniqueness
        for p in all_players:
            if len(chosen) >= 15:
                break
            # ensure overall quotas aren't broken (we already met them exactly; allow fill if underfilled)
            pos = int(p.get("position_id") or 0)
            if pos not in (1, 2, 3, 4):
                continue
            # cap the maximum by position to avoid deviating from 2/5/5/3
            max_by_pos = {1: 2, 2: 5, 3: 5, 4: 3}[pos]
            current_pos_count = len([x for x in chosen if int(x["position_id"]) == pos])
            if current_pos_count >= max_by_pos:
                continue
            if can_take(p):
                chosen.append(p)
                used_ids.add(int(p["player_id"]))
                team_id = int(p["team_id"])  # type: ignore[index]
                team_counts[team_id] = team_counts.get(team_id, 0) + 1

    if len(chosen) != 15:
        raise RuntimeError(
            f"Could not assemble a valid squad of 15 (got {len(chosen)}). Seed more players or adjust filters."
        )

    # Build payload with 11 starters, 1 captain (first), 1 vice (second)
    squad_payload: list[dict[str, Any]] = []
    for idx, p in enumerate(chosen):
        squad_payload.append(
            {
                "player_id": int(p["player_id"]),
                "is_captain": idx == 0,
                "is_vice_captain": idx == 1,
                "is_starter": idx < 11,
            }
        )
    return squad_payload


def save_squad(base: str, token: str, manager_id: int, players_payload: list[dict[str, Any]]) -> dict[str, Any]:
    url = f"{base}/managers/{manager_id}/squad"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"gw_id": None, "players": players_payload},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_squad(base: str, token: str, manager_id: int) -> dict[str, Any]:
    url = f"{base}/managers/{manager_id}/squad"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def make_transfer(base: str, token: str, manager_id: int, player_out_id: int, player_in_id: int) -> dict[str, Any]:
    url = f"{base}/managers/{manager_id}/transfers"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"gw_id": None, "player_out_id": player_out_id, "player_in_id": player_in_id},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def leaderboard(base: str) -> dict[str, Any]:
    url = f"{base}/managers/leaderboard"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def overview(base: str, token: str, manager_id: int) -> dict[str, Any]:
    url = f"{base}/managers/{manager_id}/overview"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a demo flow against the Fantasy League API")
    parser.add_argument("--base", default=_base_url_from_args(), help="API base URL, default: %(default)s")
    parser.add_argument("--email", required=True, help="Manager email to login with")
    parser.add_argument("--password", required=True, help="Manager password to login with")
    parser.add_argument("--verbose", action="store_true", help="Print full GET responses")
    args = parser.parse_args()

    base: str = str(args.base).rstrip("/")
    email: str = args.email
    password: str = args.password

    print(f"Logging in as {email} ...")
    token, manager_id = login(base, email, password)
    print(f"OK. manager_id={manager_id}")

    print("Fetching players ...")
    players_page = list_players(base, page=1, page_size=100)
    if not players_page:
        raise RuntimeError("No players found. Seed the database first.")
    if args.verbose:
        print(f"Fetched {len(players_page)} players")

    print("Selecting a valid 15-player squad ...")
    players_payload = pick_squad(players_page)
    print(f"Selected {len(players_payload)} players. Saving squad ...")
    save_resp = save_squad(base, token, manager_id, players_payload)
    print("Squad saved:", save_resp.get("message") or save_resp.get("status") or "OK")

    print("Fetching current squad ...")
    squad_resp = get_squad(base, token, manager_id)
    if args.verbose:
        print("Squad:", squad_resp)
    else:
        squad = (squad_resp or {}).get("data") or []
        print(f"Squad size: {len(squad) if isinstance(squad, list) else 'unknown'}")

    # Make a simple transfer: swap the 3rd player out with someone not already in the squad
    current_ids = {p["player_id"] for p in players_payload}
    player_out_id = players_payload[2]["player_id"]
    player_in_id = None
    for p in players_page:
        pid = int(p["player_id"])  # type: ignore[index]
        if pid not in current_ids:
            player_in_id = pid
            break
    if player_in_id is None:
        print("Could not find a replacement player for transfer; skipping.")
    else:
        print(f"Making a transfer: out {player_out_id} -> in {player_in_id} ...")
        tr_resp = make_transfer(base, token, manager_id, player_out_id, player_in_id)
        print("Transfer:", tr_resp.get("message") or tr_resp.get("status") or "OK")

    lb = leaderboard(base)
    if args.verbose:
        print("Leaderboard:", lb)
    else:
        items = (lb or {}).get("data") or []
        print(f"Leaderboard entries: {len(items) if isinstance(items, list) else 'unknown'}")

    ov = overview(base, token, manager_id)
    if args.verbose:
        print("Overview:", ov)
    else:
        print("Overview: OK")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print("HTTP error:", e.response.text if e.response is not None else str(e), file=sys.stderr)
        raise

