@echo off
REM Test Enhancement System V2 Improvements
REM =========================================

echo.
echo ================================================================================
echo TESTING ENHANCEMENT SYSTEM V2
echo ================================================================================
echo.
echo Running enhanced filtering on existing recommendations...
echo.

REM Run the enhancement system
python bet_enhancement_system.py

echo.
echo ================================================================================
echo WHAT'S NEW IN V2?
echo ================================================================================
echo.
echo 1. Scaled Correlation Penalty - Strong projections get lower penalties
echo 2. A-Tier Probability Gate - Must have >=75%% win probability
echo 3. Minutes Stability Score - Volatility detection (-5 penalty)
echo 4. Line Shading Detection - Flags potentially shaded lines
echo 5. C-Tier = Do Not Bet - Strict quality filters
echo.
echo ================================================================================
echo.
echo Output saved to: betting_recommendations_enhanced.json
echo.
echo See ENHANCEMENT_IMPROVEMENTS_V2.md for full documentation
echo.

pause
