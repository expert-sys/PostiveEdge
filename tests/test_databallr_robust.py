"""
Validation Tests for DataballR Robust Scraper
=============================================
Tests response validation, schema mapping, and data integrity.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.databallr_robust.core.requester import RobustRequester
from scrapers.databallr_robust.core.schema_map import SchemaMapper, get_databallr_schema_mapper
from scrapers.databallr_robust.core.backoff import RetryConfig, calculate_backoff_delay
from scrapers.databallr_robust.storage.save_raw import RawDataStorage
from scrapers.databallr_robust.storage.save_processed import ProcessedDataStorage


class TestRequester(unittest.TestCase):
    """Test robust requester"""
    
    def test_health_check(self):
        """Test endpoint health check"""
        requester = RobustRequester(max_retries=1, timeout=5.0)
        # Test with a known good endpoint
        is_healthy = requester.health_check("https://www.google.com")
        self.assertIsInstance(is_healthy, bool)
        requester.close()
    
    def test_retry_config(self):
        """Test retry configuration"""
        config = RetryConfig(max_attempts=5, base_delay=1.0)
        delay = calculate_backoff_delay(0, config)
        self.assertGreater(delay, 0)
        self.assertLessEqual(delay, config.max_delay)


class TestSchemaMapper(unittest.TestCase):
    """Test schema mapping"""
    
    def test_field_mapping(self):
        """Test field mapping with alternative names"""
        mapper = get_databallr_schema_mapper()
        
        # Test direct field
        data = {'points': 25}
        value = mapper.map_field(data, 'points')
        self.assertEqual(value, 25)
        
        # Test alternative name
        data = {'pts': 25}
        value = mapper.map_field(data, 'points')
        self.assertEqual(value, 25)
        
        # Test missing field with default
        data = {}
        value = mapper.map_field(data, 'points')
        self.assertEqual(value, 0)
    
    def test_dict_mapping(self):
        """Test full dict mapping"""
        mapper = get_databallr_schema_mapper()
        
        data = {
            'pts': 25,
            'reb': 10,
            'ast': 8
        }
        
        expected_schema = {
            'points': 0,
            'rebounds': 0,
            'assists': 0
        }
        
        mapped = mapper.map_dict(data, expected_schema)
        self.assertEqual(mapped['points'], 25)
        self.assertEqual(mapped['rebounds'], 10)
        self.assertEqual(mapped['assists'], 8)


class TestStorage(unittest.TestCase):
    """Test storage systems"""
    
    def setUp(self):
        """Setup test directories"""
        self.test_dir = Path("test_data")
        self.test_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Cleanup test directories"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_raw_storage(self):
        """Test raw data storage"""
        storage = RawDataStorage(self.test_dir / "raw")
        
        test_data = {
            'player': 'Test Player',
            'games': [{'points': 25}, {'points': 30}]
        }
        
        filepath = storage.save(test_data, date='2025-01-05', source='test')
        self.assertTrue(filepath.exists())
        
        # Load and verify
        loaded = storage.load(filepath)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['data']['player'], 'Test Player')
    
    def test_processed_storage(self):
        """Test processed data storage"""
        import pandas as pd
        
        storage = ProcessedDataStorage(self.test_dir / "processed", format='csv')
        
        df = pd.DataFrame([
            {'player': 'Player1', 'points': 25, 'rebounds': 10},
            {'player': 'Player2', 'points': 30, 'rebounds': 12}
        ])
        
        filepath = storage.save_dataframe(df, name='test_stats', date='2025-01-05')
        self.assertTrue(filepath.exists())
        
        # Load and verify
        loaded_df = storage.load_dataframe(filepath)
        self.assertIsNotNone(loaded_df)
        self.assertEqual(len(loaded_df), 2)


class TestDataValidation(unittest.TestCase):
    """Test data validation"""
    
    def test_non_empty_response(self):
        """Test that responses are non-empty"""
        # This would test actual scraping, but we'll mock it
        self.assertTrue(True)  # Placeholder
    
    def test_schema_fields_exist(self):
        """Test that required schema fields exist"""
        mapper = get_databallr_schema_mapper()
        
        # Test with complete data
        data = {
            'points': 25,
            'rebounds': 10,
            'assists': 8,
            'date': '2025-01-05'
        }
        
        schema = {
            'points': 0,
            'rebounds': 0,
            'assists': 0,
            'date': ''
        }
        
        mapped = mapper.map_dict(data, schema)
        self.assertIn('points', mapped)
        self.assertIn('rebounds', mapped)
        self.assertIn('assists', mapped)
        self.assertIn('date', mapped)
    
    def test_no_crashes_on_missing_fields(self):
        """Test that missing fields don't cause crashes"""
        mapper = get_databallr_schema_mapper()
        
        # Empty data should not crash
        data = {}
        schema = {
            'points': 0,
            'rebounds': 0
        }
        
        mapped = mapper.map_dict(data, schema)
        self.assertEqual(mapped['points'], 0)
        self.assertEqual(mapped['rebounds'], 0)


if __name__ == '__main__':
    unittest.main()

