@echo off
REM Quick module verification script
REM Verifies that all refactored modules can be imported

echo.
echo ================================================================================
echo   Module Structure Verification
echo ================================================================================
echo.

set PYTHONPATH=%CD%;%PYTHONPATH%

echo Testing module imports...
echo.

python -c "from nba_betting.collectors import SportsbetCollector, DataBallrValidator; print('✓ Collectors module OK')" 2>nul
if errorlevel 1 (
    echo ✗ Collectors module FAILED
    goto :error
)

python -c "from nba_betting.engines import ValueProjector; print('✓ Engines module OK')" 2>nul
if errorlevel 1 (
    echo ✗ Engines module FAILED
    goto :error
)

python -c "from models import BettingRecommendation; print('✓ Models module OK')" 2>nul
if errorlevel 1 (
    echo ✗ Models module FAILED
    goto :error
)

python -c "from config import Config; print('✓ Config module OK')" 2>nul
if errorlevel 1 (
    echo ✗ Config module FAILED
    goto :error
)

python -c "from utils.logging_config import setup_logger; print('✓ Utils module OK')" 2>nul
if errorlevel 1 (
    echo ✗ Utils module FAILED
    goto :error
)

echo.
echo ================================================================================
echo   All modules verified successfully!
echo ================================================================================
echo.
goto :end

:error
echo.
echo ================================================================================
echo   Module verification FAILED
echo ================================================================================
echo.
echo Please check that all module files exist in the correct locations.
echo.
pause
exit /b 1

:end
pause

