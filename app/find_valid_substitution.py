#!/usr/bin/env python3
"""
Script to find valid substitutions that maintain proper formation.
"""

from sqlmodel import Session, select

from app.db_models import ManagersSquad, Player, Position
from app.utils.db import engine


def get_current_squad(manager_id: str, gw_id: int = 1):
    """Get current squad with player details."""
    with Session(engine) as session:
        squad = session.exec(
            select(ManagersSquad, Player, Position)
            .join(Player, ManagersSquad.player_id == Player.player_id)
            .join(Position, Player.position_id == Position.position_id)
            .where(ManagersSquad.manager_id == manager_id)
            .where(ManagersSquad.gw_id == gw_id)
        ).all()
        
        return squad

def analyze_formation(squad_data):
    """Analyze current formation and find valid substitutions."""
    starters = [s for s in squad_data if s[0].is_starter]
    substitutes = [s for s in squad_data if not s[0].is_starter]
    
    # Count positions in starters
    pos_counts = {}
    for _, player, position in starters:
        pos_counts[position.position_name] = pos_counts.get(position.position_name, 0) + 1
    
    print("Current Formation:")
    print(f"  Starters: {len(starters)} players")
    for pos, count in pos_counts.items():
        print(f"    {pos}: {count}")
    
    print(f"\nSubstitutes: {len(substitutes)} players")
    for _, player, position in substitutes:
        print(f"    {player.player_fullname} - {position.position_name} (ID: {player.player_id})")
    
    # Find valid substitutions
    print("\nValid Substitutions:")
    
    # Required minimums
    min_required = {
        'Goalkeeper': 1,
        'Defender': 3, 
        'Midfielder': 2,
        'Forward': 1
    }
    
    valid_subs = []
    
    for starter in starters:
        starter_squad, starter_player, starter_pos = starter
        
        for sub in substitutes:
            sub_squad, sub_player, sub_pos = sub
            
            # Simulate the substitution
            new_pos_counts = pos_counts.copy()
            new_pos_counts[starter_pos.position_name] -= 1
            new_pos_counts[sub_pos.position_name] = new_pos_counts.get(sub_pos.position_name, 0) + 1
            
            # Check if formation is still valid
            is_valid = True
            for pos, min_count in min_required.items():
                if new_pos_counts.get(pos, 0) < min_count:
                    is_valid = False
                    break
            
            if is_valid:
                valid_subs.append({
                    'out': {
                        'player_id': starter_player.player_id,
                        'name': starter_player.player_fullname,
                        'position': starter_pos.position_name
                    },
                    'in': {
                        'player_id': sub_player.player_id,
                        'name': sub_player.player_fullname,
                        'position': sub_pos.position_name
                    },
                    'new_formation': new_pos_counts
                })
    
    return valid_subs

def main():
    # Replace with your actual manager ID
    manager_id = "0000198f-0ecf-6487-ac13-77b9659cdbfb"
    
    print("Analyzing squad for valid substitutions...")
    
    squad_data = get_current_squad(manager_id)
    
    if not squad_data:
        print("No squad found!")
        return
    
    valid_substitutions = analyze_formation(squad_data)
    
    if not valid_substitutions:
        print("\n❌ No valid substitutions found!")
        print("Your current formation doesn't allow any substitutions.")
        return
    
    print(f"\n✅ Found {len(valid_substitutions)} valid substitutions:")
    
    for i, sub in enumerate(valid_substitutions, 1):
        print(f"\n{i}. Swap:")
        print(f"   OUT: {sub['out']['name']} ({sub['out']['position']}) - ID: {sub['out']['player_id']}")
        print(f"   IN:  {sub['in']['name']} ({sub['in']['position']}) - ID: {sub['in']['player_id']}")
        print(f"   New formation: {sub['new_formation']}")
        
        # Create the API payload
        payload = {
            "player_out_id": sub['out']['player_id'],
            "player_in_id": sub['in']['player_id']
        }
        print(f"   API call: POST /api/v1/managers/{manager_id}/substitute?player_out_id={sub['out']['player_id']}&player_in_id={sub['in']['player_id']}")

if __name__ == "__main__":
    main()
