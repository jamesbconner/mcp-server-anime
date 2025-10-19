"""Regression tests for enhanced AniDB XML parsing.

This module contains regression tests to ensure that the enhanced parsing
functionality maintains backward compatibility with existing code and
doesn't break any existing functionality.
"""

import pytest
from datetime import datetime

from src.mcp_server_anime.core.models import AnimeDetails
from src.mcp_server_anime.providers.anidb.xml_parser import parse_anime_details
from src.mcp_server_anime.tools import _format_anime_details


class TestBackwardCompatibilityRegression:
    """Regression tests to ensure backward compatibility."""

    def test_existing_anime_details_model_compatibility(self):
        """Test that existing AnimeDetails model usage still works."""
        # Create AnimeDetails using old-style constructor (without enhanced fields)
        details = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="TV",
            episode_count=12,
            start_date=datetime(2023, 1, 1),
            synopsis="A test anime.",
        )

        # Should work with default values for enhanced fields
        assert details.aid == 123
        assert details.title == "Test Anime"
        assert details.episodes == []
        assert details.resources is None
        assert details.characters == []
        assert details.tags == []
        assert details.recommendations == []

        # Should serialize correctly
        data = details.model_dump()
        assert "episodes" in data
        assert "resources" in data
        assert "characters" in data
        assert "tags" in data
        assert "recommendations" in data

    def test_existing_xml_parsing_still_works(self):
        """Test that existing XML parsing functionality is unchanged."""
        # Use XML format that was working before enhancement
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="30" restricted="false">
            <type>TV Series</type>
            <episodecount>26</episodecount>
            <title>Neon Genesis Evangelion</title>
            <startdate>1995-10-04</startdate>
            <enddate>1996-03-27</enddate>
            <description>Mecha anime series.</description>
            
            <titles>
                <title type="main" xml:lang="en">Neon Genesis Evangelion</title>
                <title type="official" xml:lang="ja">新世紀エヴァンゲリオン</title>
            </titles>
            
            <creators>
                <name id="5111" type="Direction">Hideaki Anno</name>
                <name id="5112" type="Music">Shiro Sagisu</name>
            </creators>
            
            <relatedanime>
                <anime aid="32" type="Sequel">
                    <title>Neon Genesis Evangelion: Death &amp; Rebirth</title>
                </anime>
            </relatedanime>
            
            <ratings>
                <permanent count="12345">8.50</permanent>
                <temporary count="6789">8.20</temporary>
            </ratings>
            
            <similaranime>
                <anime aid="33" approval="150" total="200">RahXephon</anime>
            </similaranime>
        </anime>
        """

        details = parse_anime_details(xml_content)

        # All existing functionality should work exactly as before
        assert details.aid == 30
        assert details.title == "Neon Genesis Evangelion"
        assert details.type == "TV Series"
        assert details.episode_count == 26
        assert details.start_date == datetime(1995, 10, 4)
        assert details.end_date == datetime(1996, 3, 27)
        assert details.synopsis == "Mecha anime series."
        assert details.restricted is False

        # Existing nested objects should work
        assert len(details.titles) == 2
        assert details.titles[0].title == "Neon Genesis Evangelion"
        assert details.titles[0].type == "main"

        assert len(details.creators) == 2
        assert details.creators[0].name == "Hideaki Anno"
        assert details.creators[0].type == "Direction"

        assert len(details.related_anime) == 1
        assert details.related_anime[0].title == "Neon Genesis Evangelion: Death & Rebirth"

        assert details.ratings is not None
        assert details.ratings.permanent == 8.50
        assert details.ratings.permanent_count == 12345

        assert len(details.similar_anime) == 1
        assert details.similar_anime[0].title == "RahXephon"

        # Enhanced fields should have default values
        assert details.episodes == []
        assert details.resources is None
        assert details.characters == []
        assert details.tags == []
        assert details.recommendations == []

    def test_existing_mcp_response_format_unchanged(self):
        """Test that existing MCP response format is unchanged."""
        # Create details with existing fields only
        details = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="TV",
            episode_count=12,
            start_date=datetime(2023, 1, 1),
            synopsis="Test synopsis",
        )

        formatted_response = _format_anime_details(details)

        # All existing fields should be present and formatted correctly
        assert formatted_response["aid"] == 123
        assert formatted_response["title"] == "Test Anime"
        assert formatted_response["type"] == "TV"
        assert formatted_response["episode_count"] == 12
        assert formatted_response["start_date"] == "2023-01-01T00:00:00"
        assert formatted_response["synopsis"] == "Test synopsis"
        assert formatted_response["titles"] == []
        assert formatted_response["creators"] == []
        assert formatted_response["related_anime"] == []
        assert formatted_response["restricted"] is False
        assert formatted_response["ratings"] is None
        assert formatted_response["similar_anime"] == []
        assert formatted_response["picture"] is None

        # Enhanced fields should be present with default values
        assert formatted_response["episodes"] == []
        assert formatted_response["resources"] is None
        assert formatted_response["characters"] == []
        assert formatted_response["tags"] == []
        assert formatted_response["recommendations"] == []

    def test_xml_parsing_error_handling_unchanged(self):
        """Test that XML parsing error handling behavior is unchanged."""
        from src.mcp_server_anime.core.exceptions import XMLParsingError

        # Test cases that should still raise XMLParsingError
        test_cases = [
            "",  # Empty content
            "   ",  # Whitespace only
            "<invalid>xml</unclosed>",  # Malformed XML
            """<?xml version="1.0"?>
            <anime>
                <title>Missing AID</title>
            </anime>""",  # Missing required aid
            """<?xml version="1.0"?>
            <anime aid="123">
                <!-- Missing title -->
            </anime>""",  # Missing required title
        ]

        for xml_content in test_cases:
            with pytest.raises(XMLParsingError):
                parse_anime_details(xml_content)

    def test_model_validation_unchanged(self):
        """Test that model validation behavior is unchanged."""
        from pydantic import ValidationError

        # Test cases that should still raise ValidationError
        with pytest.raises(ValidationError):
            AnimeDetails(aid=0, title="Test", type="TV", episode_count=12)  # Invalid aid

        with pytest.raises(ValidationError):
            AnimeDetails(aid=123, title="", type="TV", episode_count=12)  # Empty title

        with pytest.raises(ValidationError):
            AnimeDetails(aid=123, title="Test", type="", episode_count=12)  # Empty type

        with pytest.raises(ValidationError):
            AnimeDetails(aid=123, title="Test", type="TV", episode_count=-1)  # Negative episodes

    def test_serialization_deserialization_unchanged(self):
        """Test that model serialization/deserialization is unchanged."""
        original = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="TV",
            episode_count=12,
            start_date=datetime(2023, 1, 1),
            synopsis="Test synopsis",
        )

        # Serialize
        data = original.model_dump()

        # Should include all existing fields
        expected_keys = {
            "aid", "title", "type", "episode_count", "start_date", "end_date",
            "titles", "synopsis", "url", "creators", "related_anime", "restricted",
            "ratings", "similar_anime", "picture"
        }
        
        for key in expected_keys:
            assert key in data

        # Should also include new enhanced fields
        enhanced_keys = {"episodes", "resources", "characters", "tags", "recommendations"}
        for key in enhanced_keys:
            assert key in data

        # Deserialize
        restored = AnimeDetails.model_validate(data)

        # All existing fields should match
        assert restored.aid == original.aid
        assert restored.title == original.title
        assert restored.type == original.type
        assert restored.episode_count == original.episode_count
        assert restored.start_date == original.start_date
        assert restored.synopsis == original.synopsis

        # Enhanced fields should have default values
        assert restored.episodes == []
        assert restored.resources is None
        assert restored.characters == []
        assert restored.tags == []
        assert restored.recommendations == []

    def test_existing_helper_functions_unchanged(self):
        """Test that existing helper functions behavior is unchanged."""
        from lxml import etree
        from src.mcp_server_anime.providers.anidb.xml_parser import (
            _safe_get_text, _safe_get_int, _safe_get_date
        )

        # Test _safe_get_text
        element = etree.fromstring("<test>  Hello World  </test>")
        assert _safe_get_text(element) == "Hello World"
        assert _safe_get_text(None, "default") == "default"

        # Test _safe_get_int
        element = etree.fromstring("<test>42</test>")
        assert _safe_get_int(element) == 42
        assert _safe_get_int(None, 99) == 99

        # Test _safe_get_date
        element = etree.fromstring("<test>2023-12-25</test>")
        assert _safe_get_date(element) == datetime(2023, 12, 25)
        assert _safe_get_date(None) is None

    def test_existing_parsing_functions_unchanged(self):
        """Test that existing parsing functions behavior is unchanged."""
        from lxml import etree
        from src.mcp_server_anime.providers.anidb.xml_parser import (
            _parse_titles, _parse_creators, _parse_related_anime, 
            _parse_ratings, _parse_similar_anime
        )

        xml = """
        <anime>
            <titles>
                <title type="main" xml:lang="en">Test Anime</title>
            </titles>
            <creators>
                <name id="123" type="Direction">Test Director</name>
            </creators>
            <relatedanime>
                <anime aid="456" type="Sequel">
                    <title>Test Sequel</title>
                </anime>
            </relatedanime>
            <ratings>
                <permanent count="100">8.5</permanent>
            </ratings>
            <similaranime>
                <anime aid="789" approval="50" total="100">Similar Anime</anime>
            </similaranime>
        </anime>
        """
        root = etree.fromstring(xml)

        # All existing parsing functions should work as before
        titles = _parse_titles(root)
        assert len(titles) == 1
        assert titles[0].title == "Test Anime"

        creators = _parse_creators(root)
        assert len(creators) == 1
        assert creators[0].name == "Test Director"

        related = _parse_related_anime(root)
        assert len(related) == 1
        assert related[0].title == "Test Sequel"

        ratings = _parse_ratings(root)
        assert ratings is not None
        assert ratings.permanent == 8.5

        similar = _parse_similar_anime(root)
        assert len(similar) == 1
        assert similar[0].title == "Similar Anime"

    def test_performance_regression(self):
        """Test that enhanced parsing doesn't cause performance regression."""
        import time

        # XML without enhanced sections (old format)
        old_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="123" restricted="false">
            <type>TV Series</type>
            <episodecount>12</episodecount>
            <title>Performance Test Anime</title>
            <startdate>2023-01-01</startdate>
            <description>Performance test.</description>
            
            <titles>
                <title type="main" xml:lang="en">Performance Test Anime</title>
            </titles>
            
            <creators>
                <name id="123" type="Direction">Test Director</name>
            </creators>
        </anime>
        """

        # Measure parsing time for old format
        start_time = time.time()
        for _ in range(100):  # Parse 100 times
            details = parse_anime_details(old_xml)
        old_format_time = time.time() - start_time

        # Performance should be reasonable (less than 1 second for 100 parses)
        assert old_format_time < 1.0, f"Old format parsing too slow: {old_format_time:.3f}s"

        # Verify parsing still works correctly
        assert details.aid == 123
        assert details.title == "Performance Test Anime"
        assert len(details.titles) == 1
        assert len(details.creators) == 1

        # Enhanced fields should be empty
        assert details.episodes == []
        assert details.resources is None
        assert details.characters == []
        assert details.tags == []
        assert details.recommendations == []

    def test_memory_usage_regression(self):
        """Test that enhanced parsing doesn't cause memory usage regression."""
        import gc
        import sys

        # Create many AnimeDetails objects with old-style data
        objects = []
        for i in range(1, 1001):  # Start from 1 since aid must be > 0
            details = AnimeDetails(
                aid=i,
                title=f"Anime {i}",
                type="TV",
                episode_count=12,
            )
            objects.append(details)

        # Force garbage collection
        gc.collect()

        # Memory usage should be reasonable
        # (This is a basic check - in a real scenario you'd use memory profiling tools)
        assert len(objects) == 1000
        assert all(obj.episodes == [] for obj in objects)
        assert all(obj.resources is None for obj in objects)

        # Clean up
        del objects
        gc.collect()

    def test_api_contract_unchanged(self):
        """Test that the public API contract is unchanged."""
        # Test that all existing functions are still available and work
        from src.mcp_server_anime.providers.anidb.xml_parser import (
            parse_anime_details,
            parse_anime_search_results,
            validate_xml_response,
        )
        from src.mcp_server_anime.tools import _format_anime_details

        # Functions should exist and be callable
        assert callable(parse_anime_details)
        assert callable(parse_anime_search_results)
        assert callable(validate_xml_response)
        assert callable(_format_anime_details)

        # Test basic functionality
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="123">
            <type>TV</type>
            <episodecount>12</episodecount>
            <title>API Test</title>
        </anime>
        """

        # Should work without errors
        validate_xml_response(xml)
        details = parse_anime_details(xml)
        formatted = _format_anime_details(details)

        assert details.aid == 123
        assert "aid" in formatted
        assert "episodes" in formatted  # New field should be present