"""
Test script for StatMuse team splits scraper
"""

from scrapers.statmuse_scraper import scrape_team_splits

# Test with Detroit Pistons
team_slug = "detroit-pistons"
season = "2025-26"

print("=" * 80)
print(f"TESTING STATMUSE SPLITS SCRAPER: {team_slug}")
print("=" * 80)
print()

# Scrape splits
print("Scraping team splits (Home/Road, Wins/Losses, Conference, etc.)...")
splits = scrape_team_splits(team_slug, season, headless=False)

print()
print("=" * 80)
print(f"SPLITS EXTRACTION RESULTS")
print("=" * 80)
print()

if splits:
    print(f"Total splits extracted: {len(splits)}")
    print()

    # Group splits by common types
    location_splits = [s for s in splits if s.split_type in ["Home", "Road"]]
    result_splits = [s for s in splits if s.split_type in ["Wins", "Losses"]]
    conf_splits = [s for s in splits if "Conference" in s.split_type or s.split_type in ["Eastern", "Western"]]
    month_splits = [s for s in splits if s.split_type in ["October", "November", "December", "January", "February", "March", "April"]]

    # Display Location splits
    if location_splits:
        print("LOCATION SPLITS (Home vs Road):")
        print("-" * 40)
        for split in location_splits:
            print(f"  {split.split_type}:")
            print(f"    Games: {split.games_played}")
            print(f"    Points: {split.points} PPG")
            print(f"    Rebounds: {split.rebounds} RPG")
            print(f"    Assists: {split.assists} APG")
            print(f"    FG%: {split.fg_pct}%")
            print()

    # Display Result splits
    if result_splits:
        print("RESULT SPLITS (Wins vs Losses):")
        print("-" * 40)
        for split in result_splits:
            print(f"  {split.split_type}:")
            print(f"    Games: {split.games_played}")
            print(f"    Points: {split.points} PPG")
            print(f"    Rebounds: {split.rebounds} RPG")
            print(f"    Assists: {split.assists} APG")
            print()

    # Display Conference splits
    if conf_splits:
        print("CONFERENCE SPLITS:")
        print("-" * 40)
        for split in conf_splits:
            print(f"  vs {split.split_type}:")
            print(f"    Games: {split.games_played}")
            print(f"    Points: {split.points} PPG")
            print()

    # Display Month splits
    if month_splits:
        print("MONTHLY SPLITS:")
        print("-" * 40)
        for split in month_splits:
            print(f"  {split.split_type}:")
            print(f"    Games: {split.games_played}")
            print(f"    Points: {split.points} PPG")
            print()

    # Display all splits summary
    print("ALL SPLITS SUMMARY:")
    print("-" * 40)
    for split in splits:
        print(f"  {split.split_type}: {split.games_played} GP, {split.points} PPG, {split.rebounds} RPG, {split.assists} APG")

else:
    print("No splits extracted!")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
