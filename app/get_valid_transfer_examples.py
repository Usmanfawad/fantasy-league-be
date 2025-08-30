#!/usr/bin/env python3
"""
Script to find valid transfer examples based on current squad.
"""

from sqlmodel import Session, select
from app.db_models import Player, Position, Team, ManagersSquad, PlayerPrice
from app.utils.db import engine

def get_current_squad_players(manager_id: str, gw_id: int = 1):
    """Get current squad players with details."""
    with Session(engine) as session:
        squad = session.exec(
            select(ManagersSquad, Player, Position, Team)
            .join(Player, ManagersSquad.player_id == Player.player_id)
            .join(Position, Player.position_id == Position.position_id)
            .join(Team, Player.team_id == Team.team_id)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw_id)
        ).all()
        return squad

def get_available_players(manager_id: str, gw_id: int = 1):
    """Get all players not in current squad."""
    with Session(engine) as session:
        # Get current squad player IDs
        current_ids = session.exec(
            select(ManagersSquad.player_id)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw_id)
        ).all()
        
        # Get all players not in current squad
        available = session.exec(
            select(Player, Position, Team)
            .join(Position, Player.position_id == Position.position_id)
            .join(Team, Player.team_id == Team.team_id)
            .where(~Player.player_id.in_(current_ids))
        ).all()
        return available

def find_valid_transfers(manager_id: str, gw_id: int = 1):
    """Find valid transfer combinations."""
    current_squad = get_current_squad_players(manager_id, gw_id)
    available_players = get_available_players(manager_id, gw_id)
    
    print("Current Squad:")
    print("=" * 50)
    for squad, player, position, team in current_squad:
        print(f"ID: {player.player_id} | {player.player_fullname} | {position.position_name} | {team.team_name} | Price: {player.current_price}")
    
    print(f"\nAvailable Players (not in squad):")
    print("=" * 50)
    for player, position, team in available_players:
        print(f"ID: {player.player_id} | {player.player_fullname} | {position.position_name} | {team.team_name} | Price: {player.current_price}")
    
    # Find valid transfers (same position swaps)
    print(f"\nValid Transfer Examples (same position swaps):")
    print("=" * 50)
    
    valid_transfers = []
    for squad, current_player, current_pos, current_team in current_squad:
        for available_player, available_pos, available_team in available_players:
            # Same position swap
            if current_pos.position_id == available_pos.position_id:
                valid_transfers.append({
                    'out': {
                        'id': current_player.player_id,
                        'name': current_player.player_fullname,
                        'position': current_pos.position_name,
                        'team': current_team.team_name,
                        'price': current_player.current_price
                    },
                    'in': {
                        'id': available_player.player_id,
                        'name': available_player.player_fullname,
                        'position': available_pos.position_name,
                        'team': available_team.team_name,
                        'price': available_player.current_price
                    }
                })
    
    for i, transfer in enumerate(valid_transfers[:5], 1):  # Show first 5
        print(f"\n{i}. Swap {transfer['out']['position']}:")
        print(f"   OUT: {transfer['out']['name']} ({transfer['out']['team']}) - ID: {transfer['out']['id']} - Price: {transfer['out']['price']}")
        print(f"   IN:  {transfer['in']['name']} ({transfer['in']['team']}) - ID: {transfer['in']['id']} - Price: {transfer['in']['price']}")
        print(f"   API: POST /api/v1/managers/{manager_id}/transfer")
        print(f"   Body: {{\"player_out_id\": {transfer['out']['id']}, \"player_in_id\": {transfer['in']['id']}}}")

def main():
    # Replace with your actual manager ID
    manager_id = "0000198f-0ecf-6487-ac13-77b9659cdbfb"
    
    print("Finding valid transfer examples...")
    find_valid_transfers(manager_id)

if __name__ == "__main__":
    main()

