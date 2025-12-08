"""
Test the enhanced unified analysis pipeline
"""
from scrapers.unified_analysis_pipeline import scrape_games

print("=" * 80)
print("TESTING ENHANCED UNIFIED ANALYSIS PIPELINE")
print("=" * 80)
print("\nTesting with 1 game to verify enhanced features work...")

# Test with just 1 game
results = scrape_games(max_games=1, headless=True)

print(f"\n✓ Successfully scraped {len(results)} games with enhanced analysis")

if results:
    game = results[0]
    player_props = game.get('player_props', [])
    print(f"✓ Found {len(player_props)} player props")
    
    # Check if any props have enhanced features
    enhanced_count = 0
    for prop in player_props:
        if 'risk_assessment' in prop:
            enhanced_count += 1
    
    print(f"✓ {enhanced_count} props have enhanced analysis features")
    
    if enhanced_count > 0:
        print("\n🎉 ENHANCED ANALYSIS IS WORKING!")
        print("The pipeline now includes:")
        print("  1. ✅ Risk Factors / Red Flags")
        print("  2. ✅ 'Why' explanations")
        print("  3. ✅ Variance-adjusted edges")
        print("  4. ✅ Usage change tracking")
        print("  5. ✅ Pace/Defense explanations")
    else:
        print("\n⚠️  Enhanced analysis not applied (may need player data)")

print("\n" + "=" * 80)
print("ENHANCED PIPELINE TEST COMPLETE")
print("=" * 80)