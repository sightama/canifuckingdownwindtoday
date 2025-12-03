# ABOUTME: Tests for parsing swell direction from NOAA forecast text
# ABOUTME: Verifies extraction of compass directions from various text formats

import pytest
from app.weather.sources import NOAAClient


class TestSwellDirectionParsing:
    """Tests for _parse_swell_direction method"""

    def setup_method(self):
        self.client = NOAAClient()

    def test_parse_northeast_swell_basic(self):
        """Parse 'Northeast swell 3 to 5 ft' format"""
        text = "Northeast swell 3 to 5 ft. Winds from the west."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"

    def test_parse_ne_abbreviation(self):
        """Parse 'NE swell' abbreviation format"""
        text = "Seas 2 to 3 ft. NE swell around 4 ft."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"

    def test_parse_swell_from_direction(self):
        """Parse 'swell from the NE' format"""
        text = "Winds west 10 kt. Swell from the northeast 2 to 4 ft."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"

    def test_parse_southerly_swell(self):
        """Parse southern swell directions"""
        text = "South swell 2 to 3 ft building to 4 ft."
        result = self.client._parse_swell_direction(text)
        assert result == "S"

    def test_parse_sse_swell(self):
        """Parse SSE direction"""
        text = "SSE swell 3 ft. Light winds."
        result = self.client._parse_swell_direction(text)
        assert result == "SSE"

    def test_no_swell_returns_none(self):
        """Return None when no swell direction found"""
        text = "Winds north 15 kt. Seas 2 ft."
        result = self.client._parse_swell_direction(text)
        assert result is None

    def test_mixed_case_handling(self):
        """Handle various capitalizations"""
        text = "NORTHEAST SWELL 4 FT."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"
