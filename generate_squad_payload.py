s#!/usr/bin/env python3
"""
Script to generate a valid squad payload for the Fantasy League API.
This script queries the database to get actual player IDs and positions,
then creates a valid squad that satisfies all requirements.
"""

import json
from sqlmodel import Session, select
from app.db_models import Player, Position
from app.utils.db import engine

def get_players_by_position():
    """Get all players grouped by position."""
    with Session(engine) as session:
        # Get all players with their positions
        players = session.exec(
            select(Player, Position)
            .join(Position, Player.position_id == Position.position_id)
            .order_by(Player.player_id)
        ).all()
        
        # Group by position
        positions = {}
        for player, position in players:
            if position.position_name not in positions:
                positions[position.position_name] = []
            positions[position.position_name].append({
                'player_id': player.player_id,
                'name': player.player_fullname,
                'team_id': player.team_id,
                'position_id': player.position_id
            })
        
        return positions

def create_valid_squad(players_by_position):
    """Create a valid squad that satisfies all requirements."""
    squad = []
    
    # Required quotas
    required = {
        'Goalkeeper': 2,
        'Defender': 5, 
        'Midfielder': 5,
        'Forward': 3
    }
    
    # Track team counts to ensure max 3 per team
    team_counts = {}
    
    # Add players for each position
    for position_name, count in required.items():
        if position_name not in players_by_position:
            print(f"ERROR: No {position_name} players found in database!")
            return None
            
        available_players = players_by_position[position_name]
        
        for i in range(count):
            # Find a player that doesn't exceed team limit
            selected_player = None
            for player in available_players:
                team_id = player['team_id']
                if team_counts.get(team_id, 0) < 3:
                    selected_player = player
                    team_counts[team_id] = team_counts.get(team_id, 0) + 1
                    available_players.remove(player)  # Remove to avoid duplicates
                    break
            
            if not selected_player:
                print(f"ERROR: Could not find enough {position_name} players without exceeding team limits!")
                return None
            
            # Add to squad
            squad.append({
                'player_id': selected_player['player_id'],
                'is_captain': len(squad) == 0,  # First player is captain
                'is_vice_captain': len(squad) == 1,  # Second player is vice-captain
                'is_starter': len(squad) < 11,  # First 11 are starters
                'name': selected_player['name'],  # For reference
                'position': position_name  # For reference
            })
    
    return squad

def main():
    print("Generating valid squad payload...")
    
    # Get players from database
    players_by_position = get_players_by_position()
    
    if not players_by_position:
        print("ERROR: No players found in database!")
        return
    
    print(f"Found players:")
    for position, players in players_by_position.items():
        print(f"  {position}: {len(players)} players")
    
    # Create valid squad
    squad = create_valid_squad(players_by_position)
    
    if not squad:
        print("ERROR: Could not create valid squad!")
        return
    
    # Create payload
    payload = {
        "gw_id": 1,  # You may need to change this to match your gameweek
        "players": [
            {
                "player_id": player['player_id'],
                "is_captain": player['is_captain'],
                "is_vice_captain": player['is_vice_captain'],
                "is_starter": player['is_starter']
            }
            for player in squad
        ]
    }
    
    print("\n" + "="*50)
    print("VALID SQUAD PAYLOAD:")
    print("="*50)
    print(json.dumps(payload, indent=2))
    
    print("\n" + "="*50)
    print("SQUAD BREAKDOWN:")
    print("="*50)
    starters = [p for p in squad if p['is_starter']]
    subs = [p for p in squad if not p['is_starter']]
    
    print(f"Starters ({len(starters)}):")
    for player in starters:
        captain_vc = ""
        if player['is_captain']:
            captain_vc = " (C)"
        elif player['is_vice_captain']:
            captain_vc = " (VC)"
        print(f"  {player['name']} - {player['position']}{captain_vc}")
    
    print(f"\nSubstitutes ({len(subs)}):")
    for player in subs:
        print(f"  {player['name']} - {player['position']}")
    
    # Verify team distribution
    team_distribution = {}
    for player in squad:
        # We need to get team info from the original data
        for pos_players in players_by_position.values():
            for p in pos_players:
                if p['player_id'] == player['player_id']:
                    team_id = p['team_id']
                    team_distribution[team_id] = team_distribution.get(team_id, 0) + 1
                    break
    
    print(f"\nTeam distribution:")
    for team_id, count in sorted(team_distribution.items()):
        print(f"  Team {team_id}: {count} players")

if __name__ == "__main__":
    main()

