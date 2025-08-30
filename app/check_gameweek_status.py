e#!/usr/bin/env python3
"""
Script to check current gameweek statuses and help with transfer window issues.
"""

from sqlmodel import Session, select
from app.db_models import Gameweek
from app.utils.db import engine

def check_gameweek_statuses():
    """Check all gameweeks and their current status."""
    with Session(engine) as session:
        gameweeks = session.exec(
            select(Gameweek)
            .order_by(Gameweek.gw_number)
        ).all()
        
        print("Current Gameweek Statuses:")
        print("=" * 50)
        
        for gw in gameweeks:
            print(f"GW {gw.gw_number}: {gw.status}")
            print(f"  Start: {gw.start_date}")
            print(f"  End: {gw.end_date}")
            print(f"  Updated: {gw.updated_at}")
            print()
        
        # Check for open gameweek
        open_gw = session.exec(
            select(Gameweek)
            .where(Gameweek.status == "open")
            .order_by(Gameweek.gw_number.desc())
            .limit(1)
        ).first()
        
        if open_gw:
            print(f"✅ Transfer window is OPEN for GW {open_gw.gw_number}")
        else:
            print("❌ No transfer window currently open")
            print("\nTo open a transfer window, you need to:")
            print("1. Set a gameweek status to 'open'")
            print("2. Or activate a new gameweek (which will set the previous one to 'completed')")

def open_transfer_window(gw_number: int):
    """Open transfer window for a specific gameweek."""
    with Session(engine) as session:
        gw = session.exec(
            select(Gameweek)
            .where(Gameweek.gw_number == gw_number)
        ).first()
        
        if not gw:
            print(f"❌ Gameweek {gw_number} not found")
            return
        
        print(f"Opening transfer window for GW {gw_number}...")
        gw.status = "open"
        session.add(gw)
        session.commit()
        print(f"✅ Transfer window now OPEN for GW {gw_number}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "open":
        if len(sys.argv) > 2:
            gw_number = int(sys.argv[2])
            open_transfer_window(gw_number)
        else:
            print("Usage: python -c 'from app.check_gameweek_status import open_transfer_window; open_transfer_window(1)'")
    else:
        check_gameweek_statuses()

