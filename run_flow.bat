@echo off
REM Post-login flow script for Fantasy League API (Windows)
REM 1) Paste your JWT access token and Manager ID below

set BASE=http://localhost:8000/api/v1
set TOKEN=PASTE_YOUR_JWT_HERE
set ME_ID=PASTE_YOUR_MANAGER_ID_HERE

IF "%TOKEN%"=="PASTE_YOUR_JWT_HERE" (
  echo Please edit run_flow.bat and paste your JWT into TOKEN and your manager id into ME_ID.
  goto :eof
)
IF "%ME_ID%"=="PASTE_YOUR_MANAGER_ID_HERE" (
  echo Please edit run_flow.bat and paste your manager id into ME_ID.
  goto :eof
)

REM 2) Verify current manager
curl -X GET %BASE%/auth/me ^
  -H "Authorization: Bearer %TOKEN%"

REM 3) List players (first page)
curl -X GET "%BASE%/players?page=1&page_size=20&active_only=true"

REM 4) Players stats (sorted by goals)
curl -X GET "%BASE%/players/stats?sort=goals&page=1&page_size=20"

REM 5) Save a 15-player squad for the active gameweek
REM NOTE: Replace the player_id values with valid ones from the list you fetched above
curl -X POST %BASE%/managers/%ME_ID%/squad ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{ \"gw_id\": null, \"players\": [
    {\"player_id\": 1, \"is_captain\": true, \"is_starter\": true},
    {\"player_id\": 2, \"is_vice_captain\": true, \"is_starter\": true},
    {\"player_id\": 3, \"is_starter\": true},
    {\"player_id\": 4, \"is_starter\": true},
    {\"player_id\": 5, \"is_starter\": true},
    {\"player_id\": 6, \"is_starter\": true},
    {\"player_id\": 7, \"is_starter\": true},
    {\"player_id\": 8, \"is_starter\": true},
    {\"player_id\": 9, \"is_starter\": true},
    {\"player_id\": 10, \"is_starter\": true},
    {\"player_id\": 11, \"is_starter\": true},
    {\"player_id\": 12, \"is_starter\": false},
    {\"player_id\": 13, \"is_starter\": false},
    {\"player_id\": 14, \"is_starter\": false},
    {\"player_id\": 15, \"is_starter\": false}
  ] }"

REM 6) Fetch your current squad for the active gameweek
curl -X GET %BASE%/managers/%ME_ID%/squad ^
  -H "Authorization: Bearer %TOKEN%"

REM 7) Make a transfer (applies a 4-point penalty)
REM NOTE: Ensure player_out_id is in your squad and player_in_id is not already there
curl -X POST %BASE%/managers/%ME_ID%/transfers ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{ \"gw_id\": null, \"player_out_id\": 3, \"player_in_id\": 20 }"

REM 8) View manager overview (points summary for active gameweek)
curl -X GET %BASE%/managers/%ME_ID%/overview ^
  -H "Authorization: Bearer %TOKEN%"

REM 9) Leaderboard
curl -X GET %BASE%/managers/leaderboard

REM 10) Fixtures and scoring (example for GW 1)
curl -X GET %BASE%/fixtures
curl -X GET %BASE%/scoring/1

echo.
echo Flow complete. Review responses above.
pause


