
# Game Platform API — Cursor-Readable Spec

This document converts the provided PDF brief into a clean, machine-readable spec for use with Cursor or other codegen tools. It captures flows, endpoints, validations, and response contracts.

---

## 0) Auth & Security

- **Password Hashing**: bcrypt (salt rounds: 10)
- **Tokens**: JWT (HS256), expires in 7 days
- **HTTPS**: Enforced
- **Login Rate Limit**: Max 5 attempts/minute
- **JWT Payloads**
  - Manager: `{ manager_id, email, squad_name }`
  - Admin: `{ admin_id, username }`
- **Config**
  - `JWT_SECRET` in environment
  - Prefer middleware for HTTPS-only and rate limiting

---

## 1) Auth Endpoints

### 1.1 Sign Up — `POST /auth/sign-up`
- **Table**: `managers`
- **Body fields**: `firstname, lastname, email, password, birthdate, city, fav_team, fav_player, squad_name`
- **Flow**:
  1. Validate fields
  2. Ensure **email** and **squad_name** are unique
  3. Hash password (bcrypt, salt=10)
  4. Insert into `managers`
  5. Return `manager_id` and success
- **Responses**
  - 200: `{ "status": "success", "manager_id": 101, "message": "Account created successfully" }`
  - 400: `{ "status": "error", "message": "Email already registered." }`
  - 400: `{ "status": "error", "message": "Squad name already taken." }`

### 1.2 Sign In — `POST /auth/login`
- **Table**: `managers`
- **Body**: `email, password`
- **Responses**
  - 200: `{ "status": "success", "token": "<jwt>", "manager_id": 101, "squad_name": "Dream Team" }`
  - 401: `{ "status": "error", "message": "Invalid email or password." }`
  - Admin variant: `{ "status": "error", "message": "Invalid username or password." }`

---

## 2) Players

### 2.1 List Players — `GET /players`
- **Purpose**: Retrieve list of **active** players for selection
- **Tables**: `players, teams, positions, player_prices, gameweeks`
- **Query params (optional)**:
  - `team_id`
  - `position_id`
  - `search` (partial name)
- **Constraints**: `players.is_active = true`
- **Returns (per item)**: `player_id, fullname, team_name, position_name, price, player_pic_url`

### 2.2 Get Player — `GET /players/{player_id}`
- **Purpose**: Retrieve a single player's details
- **Tables**: `players, teams, positions, player_prices, gameweeks, events, scoring_rules, managers`
- **Returns**: `player_id, fullname, team_name, position_name, price, player_pic_url, total_points, selected_percentage`
- **Validations**: `player_id` exists, player is active
- **Condition**: Use latest active gameweek data
- **Errors**
  - 404: `"Player with ID {player_id} not found or inactive."`

### 2.3 Players Stats Leaderboard — `GET /players/stats`
- **Purpose**: Global stats explorer with sorting/filtering
- **Tables**: `players, teams, positions, player_prices, player_stats, gameweeks, managers`
- **Query params (filters)**: `team_id, position_id, search, min_price, max_price`
- **Sort**: `cumulative_points` (default), `gameweek_points, goals, assists, bonus_points, price`
- **Returns**: `player_id, fullname, team_name, position_name, current_price, cumulative_points, gameweek_points, goals, assists, bonus_points, yellow_cards, red_cards, clean_sheets, minutes_played, selection_percentage`

---

## 3) Squad Selection

### Rules
- **Total players**: 15 (11 starters, 4 bench)
- **Position quotas**: e.g., `2 GK, 5 DEF, 5 MID, 3 FWD` (configurable)
- **Uniqueness**: No duplicate `player_id`
- **Per-team cap**: Max **3** players from the same team
- **Captaincy**: Exactly **1** captain and **1** vice-captain
- **Timing**: Only before **gameweek** deadline
- **Wallet**: Sum of selected players ≤ wallet balance

### 3.1 Save Squad — `POST /managers/{manager_id}/squad`
- **Table(s)**: `managers_squad`
- **Body**: `gw_id, players[]` with roles:
  - `player_id, is_captain, is_vice_captain, is_starter, on_bench`
- **Validations**:
  - Manager exists
  - `gw_id` is valid and not completed
  - Valid `player_id`s
  - Exactly one captain & vice-captain
  - No duplicates
  - ≤ 3 players per real team
- **Behavior**:
  - Overwrite existing squad for same manager + `gw_id`
- **Responses**
  - 200: `{ "status": "success", "message": "Squad successfully saved." }`
  - 400 / 404 / 500 with appropriate messages
- **Condition**: Allowed only for **active/upcoming** gameweeks

### 3.2 Get Manager Squad — `GET /managers/{manager_id}/squad`
- **Purpose**: Retrieve squad for the **latest active** gameweek and compute GW points
- **Tables**: `managers_squad, players, teams, positions, player_prices, gameweeks, events, scoring_rules`
- **Returns**: `manager_id, squad_name, gw_id, gw_number, player_id, fullname, team_name, position_name, price, player_pic_url, is_captain, is_vice_captain, is_starter, on_bench, points_this_gw`
- **Errors**:
  - 404 if manager not found or squad not set

### 3.3 Manager Overview — `GET /managers/{manager_id}/overview`
- **Purpose**:
  - Manager’s **total points** this gameweek
  - **Average** points across all managers
  - **Top earner** (manager_id & points) for the gameweek
- **Tables**: `managers, managers_squad, players, player_prices, gameweeks, events, scoring_rules`
- **Returns**: `manager_id, squad_name, gw_id, gw_number, manager_total_points, average_manager_points, top_earner_manager_id, top_earner_points`
- **Note**: Averages and top-earner are **computed** for latest active gameweek

---

## 4) Transfers

### Mechanics
- **Budget**:
  - Wallet after transfer = `current_wallet + OUT.price - IN.price`
  - Block transfer if wallet < 0
  - Prices come from **latest active gameweek**
- **Limits & Penalties**:
  - 1 **free** transfer per GW
  - Each extra transfer = **-4** points applied to GW points
- **Restrictions**:
  - Only while gameweek is **open**
  - Cannot add a player already in squad
  - Must respect position & per-team caps and wallet

### 4.1 Make Transfer — `POST /managers/{manager_id}/transfers`
- **Tables**: `managers, managers_squad, players, transfers, gameweeks`
- **Body**: `gw_id, player_out_id, player_in_id`
- **Validations**: Manager exists; `gw_id` active; `player_in` active; squad constraints; wallet check
- **Behavior**: **Atomic** update of squad, wallet, and transfer record
- **Responses**:
  - 200: success + updated wallet + penalty points (if any)
  - 400/404/500 with reason; rollback on failure

---

## 5) Leaderboards

### 5.1 Managers Leaderboard — `GET /managers/leaderboard`
- **Purpose**: Sorted leaderboard for **current GW** and **cumulative season**
- **Tables**: `managers, managers_squad, players, gameweeks, events, scoring_rules`
- **Returns**: `rank, manager_id, squad_name, manager_name, gw_points, cumulative_points`

---

## 6) DB Entities (suggested)

> These are indicative; align with your existing schema naming.

- `managers(manager_id, firstname, lastname, email (unique), password_hash, birthdate, city, squad_name (unique), fav_team, fav_player, wallet)`
- `players(player_id, fullname, team_id, position_id, is_active, player_pic_url)`
- `teams(team_id, name)`
- `positions(position_id, code, name)`
- `gameweeks(gw_id, number, deadline_at, status: open|closed|completed)`
- `player_prices(player_id, gw_id, price)`
- `player_stats(player_id, gw_id, goals, assists, bonus_points, yellow_cards, red_cards, clean_sheets, minutes_played, points)`
- `managers_squad(manager_id, gw_id, player_id, is_captain, is_vice_captain, is_starter, on_bench)`
- `events(event_id, player_id, gw_id, type, value)`
- `transfers(transfer_id, manager_id, gw_id, out_player_id, in_player_id, penalty_applied, wallet_after)`
- `scoring_rules(event_type, points)`

---

## 7) Error Schema (recommended)

```json
{
  "status": "error",
  "message": "Human-readable message",
  "code": "OPTIONAL_MACHINE_CODE"
}
```

---

## 8) Non-Functional Notes

- Enforce **rate limiting** on login and optionally on expensive endpoints.
- Prefer **idempotency** for `POST /managers/{id}/squad` (overwrite behavior acknowledged).
- Use **transactions** for transfers to ensure atomicity.
- Compute derived fields (e.g., `points_this_gw`, averages) in SQL or via service layer with caching.

---

## 9) Quick OpenAPI Scaffold (YAML)

> Minimal skeleton to drop into `openapi.yaml` and expand.

```yaml
openapi: 3.0.3
info:
  title: Game Platform API
  version: 0.1.0
servers:
  - url: /
paths:
  /auth/sign-up:
    post:
      summary: Sign up a manager
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                firstname: { type: string }
                lastname: { type: string }
                email: { type: string, format: email }
                password: { type: string, format: password }
                birthdate: { type: string, format: date }
                city: { type: string }
                fav_team: { type: string }
                fav_player: { type: string }
                squad_name: { type: string }
              required: [email, password, squad_name]
      responses:
        "200": { description: Success }
        "400": { description: Validation error }
  /auth/login:
    post:
      summary: Login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email: { type: string, format: email }
                password: { type: string, format: password }
              required: [email, password]
      responses:
        "200": { description: Token and manager info }
        "401": { description: Invalid credentials }
  /players:
    get:
      summary: List active players
      parameters:
        - in: query
          name: team_id
          schema: { type: integer }
        - in: query
          name: position_id
          schema: { type: integer }
        - in: query
          name: search
          schema: { type: string }
      responses:
        "200": { description: Players list }
  /players/{player_id}:
    get:
      summary: Get player detail
      parameters:
        - in: path
          name: player_id
          required: true
          schema: { type: integer }
      responses:
        "200": { description: Player detail }
        "404": { description: Not found }
  /players/stats:
    get:
      summary: Players stats
      responses:
        "200": { description: Stats list }
  /managers/{manager_id}/squad:
    post:
      summary: Save squad
      parameters:
        - in: path
          name: manager_id
          required: true
          schema: { type: integer }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                gw_id: { type: integer }
                players:
                  type: array
                  items:
                    type: object
                    properties:
                      player_id: { type: integer }
                      is_captain: { type: boolean }
                      is_vice_captain: { type: boolean }
                      is_starter: { type: boolean }
                      on_bench: { type: boolean }
              required: [gw_id, players]
      responses:
        "200": { description: Saved }
        "400": { description: Validation error }
        "404": { description: Not found }
    get:
      summary: Get manager squad (latest active gameweek)
      parameters:
        - in: path
          name: manager_id
          required: true
          schema: { type: integer }
      responses:
        "200": { description: Squad list }
        "404": { description: Not found }
  /managers/{manager_id}/overview:
    get:
      summary: Manager overview for active gameweek
      parameters:
        - in: path
          name: manager_id
          required: true
          schema: { type: integer }
      responses:
        "200": { description: Overview }
        "404": { description: Not found }
  /managers/leaderboard:
    get:
      summary: Managers leaderboard
      responses:
        "200": { description: Leaderboard }
  /managers/{manager_id}/transfers:
    post:
      summary: Make a transfer
      parameters:
        - in: path
          name: manager_id
          required: true
          schema: { type: integer }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                gw_id: { type: integer }
                player_out_id: { type: integer }
                player_in_id: { type: integer }
              required: [gw_id, player_out_id, player_in_id]
      responses:
        "200": { description: Transfer success }
        "400": { description: Validation error }
        "404": { description: Not found }
```

---

## 10) Frontend Notes
- Landing/launcher requires a **fade-in** animation.
- Provide clear UX for choosing players, enforcing quotas, captain/vice selection, and wallet budget.
- Display **current gameweek status** to gate actions (create team, transfers).

