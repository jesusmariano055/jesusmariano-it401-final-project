# Project Title

CourtVision — Jesus Mariano — IT401 — Assignment 1

## Project Overview

CourtVision is a basketball intelligence prototype designed for NBA player evaluation and game-strategy analysis. It is intended for basketball analysts, aspiring scouts, coaches, advanced NBA fans, and students who want a clearer way to compare player production, team roles, and matchup-relevant performance. The problem it addresses is that raw box scores and scattered online sources do not provide a structured, explainable view of what matters most when analyzing players and preparing for games.

## Preliminary Semester Project Concept

The long-term direction for CourtVision is to evolve into a full NBA intelligence platform that ingests live data from sources such as nba_api or BALDONTLIE, stores it in mySQL, and supports player comparison, trend detection, and explainable scouting recommendations. The project may be refined after Module 2, but the planned direction includes:

- a live NBA data ingestion layer
- mySQL persistence for players, teams, games, and reports
- player comparison and similarity analysis
- trend detection across multiple games or seasons
- explainable matchup scouting recommendations
- watchlist and evaluation workflows for analysts and coaches

## Current Features

This assignment covers the prototype foundation for CourtVision. The app currently includes:

- a polished homepage with branding and navigation
- a shared Jinja2 layout for consistent page structure
- a local JSON data source for player information
- an Explore page that displays NBA players and supports filtering by name, team, position, and minimum points per game
- a clean front-end layout tailored to a basketball analytics concept

## Information Model (Conceptual)

CourtVision will eventually manage a broad set of basketball data. Conceptually, the core entities include:

- Player: id, name, team, position, height, ppg, apg, rpg, spg, fg_pct, season
- Team: team_id, name, division, conference, roster summary
- Game/Matchup: game_id, date, home_team, away_team, score, venue, context
- ScoutingReport: report_id, player_id, summary, strengths, weaknesses, matchup_notes
- Watchlist: user-created list of players to monitor over time

No database schema is required yet; this is a conceptual model for the project’s future direction.

## Project Structure

The repository is organized to support future expansion while keeping A1 scoped to a local JSON dataset and Flask routes.

- app.py — Flask app factory and entry point
- config.py — configuration settings, including DATA_DIR
- routes/ — route registration and view logic
- services/ — placeholder service modules for API and AI integration
- models/ — future data model definitions
- templates/ — Jinja templates for the homepage and player explorer
- static/ — CSS and SVG assets for the application frontend
- data/ — local JSON datasets used by the prototype
- tests/ — automated tests for the app behavior

## Installation Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd project
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

3. Activate the environment:
   ```bash
   # macOS / Linux
   source .venv/bin/activate

   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open the app in a browser:
   ```text
   http://127.0.0.1:5000
   ```

## Screenshots

- Homepage: 
![alt text](image.png)
- Explore page: 
![alt text](image-1.png)
- Filtering feature: 
![alt text](image-2.png)
![alt text](image-3.png)
![alt text](image-4.png)

## Future Work

For Assignment 2, the project will expand with live NBA API ingestion, database persistence, richer analytics, and AI-backed recommendations. Planned enhancements include:

- live NBA data ingestion via API service integration
- mySQL persistence for players, teams, and game context
- search and filtering service upgrades
- analytics and scoring for player comparison and trend tracking
- AI recommendation layer to generate explainable player and matchup insights

# A1 Scope

This repository represents the Assignment 1 prototype foundation for CourtVision. The current version intentionally uses a local JSON dataset and focuses on structure, UX, filtering, and documentation rather than external data services or database persistence.
