"""
Extract text from screenshots using OCR
"""
import re
from pathlib import Path

def extract_season_results_from_ocr(text: str):
    """
    Extract season results from OCR text
    
    Looking for patterns like:
    TOR 04/12/25 123-120 W
    PHX 01/12/25 125-108 L
    """
    results = []
    
    # Pattern: Team abbreviation, date, score, W/L
    # Example: TOR 04/12/25 123-120 W
    pattern = r'([A-Z]{2,4})\s+(\d{2}/\d{2}/\d{2})\s+(\d{2,3})-(\d{2,3})\s+([WL])'
    
    matches = re.findall(pattern, text)
    
    for match in matches:
        opponent, date, score_for, score_against, result = match
        results.append({
            'opponent': opponent,
            'date': date,
            'score_for': int(score_for),
            'score_against': int(score_against),
            'result': result
        })
    
    return results

def extract_head_to_head_from_ocr(text: str):
    """
    Extract head-to-head data from OCR text
    
    Looking for patterns like:
    Sat 8 Mar 2025 - TD Garden
    Q1 Q2 Q3 Q4 FT
    LAL 33 21 13 34 101 L
    BOS 33 25 29 24 111 W
    """
    h2h_games = []
    
    # Look for date and venue pattern
    date_venue_pattern = r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+\w+\s+\d{4})\s*-\s*(.+?)(?=\n|$)'
    
    # Look for score lines
    score_pattern = r'([A-Z]{2,4})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([WL])'
    
    date_matches = re.findall(date_venue_pattern, text)
    score_matches = re.findall(score_pattern, text)
    
    # Try to pair dates with scores
    for i, (date, venue) in enumerate(date_matches):
        # Get the next 2 score lines (away and home)
        if i * 2 + 1 < len(score_matches):
            away_scores = score_matches[i * 2]
            home_scores = score_matches[i * 2 + 1]
            
            h2h_games.append({
                'date': date,
                'venue': venue.strip(),
                'away_team': away_scores[0],
                'away_q1': int(away_scores[1]),
                'away_q2': int(away_scores[2]),
                'away_q3': int(away_scores[3]),
                'away_q4': int(away_scores[4]),
                'away_final': int(away_scores[5]),
                'away_result': away_scores[6],
                'home_team': home_scores[0],
                'home_q1': int(home_scores[1]),
                'home_q2': int(home_scores[2]),
                'home_q3': int(home_scores[3]),
                'home_q4': int(home_scores[4]),
                'home_final': int(home_scores[5]),
                'home_result': home_scores[6],
            })
    
    return h2h_games

def extract_from_screenshots():
    """
    Main function to extract data from screenshots using OCR
    """
    print("=" * 80)
    print("OCR TEXT EXTRACTION")
    print("=" * 80)
    
    screenshots_dir = Path("debug/screenshots")
    
    if not screenshots_dir.exists():
        print("\n✗ Screenshots directory not found!")
        print("Run screenshot_scraper.py first to capture screenshots.")
        return
    
    # Check if easyocr is installed
    try:
        import easyocr
        print("\n✓ EasyOCR is installed")
    except ImportError:
        print("\n✗ EasyOCR not installed!")
        print("Install it with: pip install easyocr")
        print("\nAlternatively, you can manually read the screenshots")
        print("and enter the data, or use a different OCR tool.")
        return
    
    print("\nInitializing OCR reader (this may take a moment)...")
    reader = easyocr.Reader(['en'])
    
    # Process full page screenshot
    full_page_img = screenshots_dir / "full_page.png"
    if full_page_img.exists():
        print(f"\nProcessing: {full_page_img}")
        print("This may take 30-60 seconds...")
        
        result = reader.readtext(str(full_page_img))
        
        # Combine all text
        full_text = "\n".join([text for (bbox, text, prob) in result])
        
        # Save extracted text
        text_file = screenshots_dir / "extracted_text.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"✓ Saved extracted text to: {text_file}")
        
        # Extract season results
        print("\nExtracting season results...")
        season_results = extract_season_results_from_ocr(full_text)
        print(f"✓ Found {len(season_results)} season results")
        
        if season_results:
            print("\nSample results:")
            for result in season_results[:5]:
                print(f"  {result['opponent']} {result['date']} {result['score_for']}-{result['score_against']} ({result['result']})")
        
        # Extract head-to-head
        print("\nExtracting head-to-head data...")
        h2h_games = extract_head_to_head_from_ocr(full_text)
        print(f"✓ Found {len(h2h_games)} head-to-head games")
        
        if h2h_games:
            print("\nSample H2H:")
            for game in h2h_games[:2]:
                print(f"  {game['date']} at {game['venue']}")
                print(f"    {game['away_team']}: {game['away_final']} ({game['away_result']})")
                print(f"    {game['home_team']}: {game['home_final']} ({game['home_result']})")
        
        # Save results
        import json
        results_file = screenshots_dir / "ocr_results.json"
        with open(results_file, "w") as f:
            json.dump({
                'season_results': season_results,
                'head_to_head': h2h_games
            }, f, indent=2)
        print(f"\n✓ Saved results to: {results_file}")
    
    else:
        print(f"\n✗ Screenshot not found: {full_page_img}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    extract_from_screenshots()
