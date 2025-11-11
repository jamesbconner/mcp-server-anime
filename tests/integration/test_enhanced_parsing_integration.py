"""Integration tests for enhanced AniDB XML parsing.

This module contains integration tests that verify the complete flow
from XML parsing to MCP tool response formatting with enhanced fields.
"""

from datetime import datetime

from src.mcp_server_anime.providers.anidb.xml_parser import parse_anime_details
from src.mcp_server_anime.tools import _format_anime_details


class TestEnhancedParsingIntegration:
    """Integration tests for enhanced parsing functionality."""

    def test_complete_enhanced_parsing_flow(self):
        """Test complete flow from XML parsing to MCP response formatting."""
        # Realistic XML response with enhanced data
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="30" restricted="false">
            <type>TV Series</type>
            <episodecount>26</episodecount>
            <title>Neon Genesis Evangelion</title>
            <startdate>1995-10-04</startdate>
            <enddate>1996-03-27</enddate>
            <description>A mecha anime series about teenage pilots.</description>

            <episodes>
                <episode id="1">
                    <title>Angel Attack</title>
                    <airdate>1995-10-04</airdate>
                    <summary>The first Angel appears in Tokyo-3.</summary>
                    <length>24</length>
                </episode>
                <episode id="2">
                    <title>The Beast</title>
                    <airdate>1995-10-11</airdate>
                    <summary>Shinji begins training as an Eva pilot.</summary>
                    <length>24</length>
                </episode>
            </episodes>

            <resources>
                <resource type="1" externalentity="30" url="https://myanimelist.net/anime/30">
                    MyAnimeList Entry
                </resource>
                <resource type="43" externalentity="tt0112159">
                    IMDB Entry
                </resource>
                <resource type="4" url="https://www.evangelion.co.jp/">
                    Official Site
                </resource>
            </resources>

            <characters>
                <character id="89">
                    <name>Shinji Ikari</name>
                    <description>The main protagonist, a reluctant Eva pilot.</description>
                    <charactertype>Main</charactertype>
                    <seiyuu>
                        <seiyuu id="123" lang="ja">Megumi Ogata</seiyuu>
                        <seiyuu id="456" lang="en">Spike Spencer</seiyuu>
                    </seiyuu>
                </character>
                <character id="90">
                    <name>Rei Ayanami</name>
                    <description>The mysterious First Child.</description>
                    <charactertype>Main</charactertype>
                    <seiyuu>
                        <seiyuu id="789" lang="ja">Megumi Hayashibara</seiyuu>
                    </seiyuu>
                </character>
            </characters>

            <tags>
                <tag id="2274" weight="600" spoiler="false" verified="true">
                    <name>robot</name>
                    <description>Mecha/robot anime featuring giant robots.</description>
                </tag>
                <tag id="2605" weight="500" spoiler="false" verified="true">
                    <name>dynamic</name>
                    <description>Fast-paced action sequences.</description>
                </tag>
                <tag id="2931" weight="400" spoiler="true" verified="true">
                    <name>psychological</name>
                    <description>Deep psychological themes and character development.</description>
                </tag>
            </tags>

            <recommendations>
                <recommendation type="Must See" uid="12345">
                    <text>A masterpiece of anime that redefined the mecha genre. Essential viewing for any anime fan.</text>
                </recommendation>
                <recommendation type="Recommended" uid="67890">
                    <text>Great animation and complex characters, though the ending can be confusing.</text>
                </recommendation>
            </recommendations>
        </anime>
        """

        # Parse the XML
        details = parse_anime_details(xml_content)

        # Verify basic fields
        assert details.aid == 30
        assert details.title == "Neon Genesis Evangelion"
        assert details.type == "TV Series"
        assert details.episode_count == 26
        assert details.start_date == datetime(1995, 10, 4)
        assert details.end_date == datetime(1996, 3, 27)

        # Verify enhanced fields
        assert len(details.episodes) == 2
        assert len(details.characters) == 2
        assert len(details.tags) == 3
        assert len(details.recommendations) == 2
        assert details.resources is not None

        # Verify episode data
        ep1 = details.episodes[0]
        assert ep1.episode_number == 1
        assert ep1.title == "Angel Attack"
        assert ep1.air_date == datetime(1995, 10, 4)
        assert "first Angel" in ep1.description
        assert ep1.length == 24

        # Verify character data
        shinji = details.characters[0]
        assert shinji.name == "Shinji Ikari"
        assert shinji.id == 89
        assert "protagonist" in shinji.description
        assert shinji.character_type == "Main"
        assert len(shinji.voice_actors) == 2

        # Verify voice actor data
        va_jp = shinji.voice_actors[0]
        assert va_jp.name == "Megumi Ogata"
        assert va_jp.id == 123
        assert va_jp.language == "ja"

        # Verify resource data
        assert len(details.resources.myanimelist) == 1
        assert len(details.resources.imdb) == 1
        assert len(details.resources.official_sites) == 1

        mal_resource = details.resources.myanimelist[0]
        assert mal_resource.type == "MyAnimeList"
        assert mal_resource.identifier == "30"
        assert "myanimelist.net" in mal_resource.url

        # Verify tag data (should be sorted by weight)
        assert details.tags[0].weight == 600  # Highest weight first
        assert details.tags[0].name == "robot"
        assert details.tags[0].spoiler is False
        assert details.tags[0].verified is True

        # Check spoiler tag
        psych_tag = next(tag for tag in details.tags if tag.name == "psychological")
        assert psych_tag.spoiler is True

        # Verify recommendation data
        rec1 = details.recommendations[0]
        assert rec1.type == "Must See"
        assert rec1.user_id == 12345
        assert "masterpiece" in rec1.text

        # Test MCP response formatting
        formatted_response = _format_anime_details(details)

        # Verify formatted response structure
        assert "episodes" in formatted_response
        assert "resources" in formatted_response
        assert "characters" in formatted_response
        assert "tags" in formatted_response
        assert "recommendations" in formatted_response

        # Verify formatted episodes
        formatted_episodes = formatted_response["episodes"]
        assert len(formatted_episodes) == 2
        assert formatted_episodes[0]["episode_number"] == 1
        assert formatted_episodes[0]["title"] == "Angel Attack"
        assert formatted_episodes[0]["air_date"] == "1995-10-04T00:00:00"

        # Verify formatted resources
        formatted_resources = formatted_response["resources"]
        assert len(formatted_resources["myanimelist"]) == 1
        assert len(formatted_resources["imdb"]) == 1
        assert len(formatted_resources["official_sites"]) == 1

        # Verify formatted characters
        formatted_characters = formatted_response["characters"]
        assert len(formatted_characters) == 2
        assert formatted_characters[0]["name"] == "Shinji Ikari"
        assert len(formatted_characters[0]["voice_actors"]) == 2

        # Verify formatted tags
        formatted_tags = formatted_response["tags"]
        assert len(formatted_tags) == 3
        assert formatted_tags[0]["weight"] == 600
        assert formatted_tags[0]["spoiler"] is False

        # Verify formatted recommendations
        formatted_recs = formatted_response["recommendations"]
        assert len(formatted_recs) == 2
        assert formatted_recs[0]["type"] == "Must See"
        assert formatted_recs[0]["user_id"] == 12345

    def test_enhanced_parsing_with_minimal_data(self):
        """Test enhanced parsing with minimal enhanced data."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="123" restricted="false">
            <type>Movie</type>
            <episodecount>1</episodecount>
            <title>Test Movie</title>

            <episodes>
                <episode id="1">
                    <title>Full Movie</title>
                    <length>120</length>
                </episode>
            </episodes>

            <tags>
                <tag id="100">
                    <name>movie</name>
                </tag>
            </tags>
        </anime>
        """

        details = parse_anime_details(xml_content)
        formatted_response = _format_anime_details(details)

        # Should have basic and some enhanced fields
        assert details.aid == 123
        assert len(details.episodes) == 1
        assert len(details.tags) == 1
        assert len(details.characters) == 0
        assert len(details.recommendations) == 0
        assert details.resources is None

        # Formatted response should handle None/empty fields gracefully
        assert formatted_response["resources"] is None
        assert formatted_response["characters"] == []
        assert formatted_response["recommendations"] == []
        assert len(formatted_response["episodes"]) == 1
        assert len(formatted_response["tags"]) == 1

    def test_enhanced_parsing_performance(self):
        """Test that enhanced parsing doesn't significantly impact performance."""
        import time

        # Large XML with many enhanced elements
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="456" restricted="false">
            <type>TV Series</type>
            <episodecount>100</episodecount>
            <title>Long Running Series</title>

            <episodes>
        """

        # Add many episodes
        for i in range(1, 51):  # 50 episodes
            xml_content += f"""
                <episode id="{i}">
                    <title>Episode {i}</title>
                    <airdate>2023-01-{i:02d}</airdate>
                    <length>24</length>
                </episode>
            """

        xml_content += """
            </episodes>

            <characters>
        """

        # Add many characters
        for i in range(1, 21):  # 20 characters
            xml_content += f"""
                <character id="{i}">
                    <name>Character {i}</name>
                    <description>Description for character {i}.</description>
                </character>
            """

        xml_content += """
            </characters>

            <tags>
        """

        # Add many tags
        for i in range(1, 31):  # 30 tags
            xml_content += f"""
                <tag id="{i}" weight="{500 - i * 10}">
                    <name>tag{i}</name>
                    <description>Description for tag {i}.</description>
                </tag>
            """

        xml_content += """
            </tags>
        </anime>
        """

        # Measure parsing time
        start_time = time.time()
        details = parse_anime_details(xml_content)
        parsing_time = time.time() - start_time

        # Measure formatting time
        start_time = time.time()
        formatted_response = _format_anime_details(details)
        formatting_time = time.time() - start_time

        # Verify data was parsed correctly
        assert len(details.episodes) == 50
        assert len(details.characters) == 20
        assert len(details.tags) == 30

        # Performance should be reasonable (less than 1 second for this amount of data)
        assert parsing_time < 1.0, f"Parsing took too long: {parsing_time:.3f}s"
        assert formatting_time < 1.0, (
            f"Formatting took too long: {formatting_time:.3f}s"
        )

        # Verify formatted response
        assert len(formatted_response["episodes"]) == 50
        assert len(formatted_response["characters"]) == 20
        assert len(formatted_response["tags"]) == 30

    def test_enhanced_parsing_backward_compatibility(self):
        """Test that enhanced parsing maintains backward compatibility."""
        # Old-style XML without enhanced sections
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <anime aid="789" restricted="false">
            <type>OVA</type>
            <episodecount>6</episodecount>
            <title>Classic Anime</title>
            <startdate>1990-01-01</startdate>
            <description>A classic anime from the 90s.</description>

            <titles>
                <title type="main" xml:lang="en">Classic Anime</title>
                <title type="official" xml:lang="ja">クラシックアニメ</title>
            </titles>

            <creators>
                <name id="123" type="Direction">Famous Director</name>
            </creators>
        </anime>
        """

        details = parse_anime_details(xml_content)
        formatted_response = _format_anime_details(details)

        # Basic fields should work as before
        assert details.aid == 789
        assert details.title == "Classic Anime"
        assert details.type == "OVA"
        assert details.episode_count == 6
        assert len(details.titles) == 2
        assert len(details.creators) == 1

        # Enhanced fields should have default values
        assert details.episodes == []
        assert details.resources is None
        assert details.characters == []
        assert details.tags == []
        assert details.recommendations == []

        # Formatted response should include enhanced fields with default values
        assert "episodes" in formatted_response
        assert "resources" in formatted_response
        assert "characters" in formatted_response
        assert "tags" in formatted_response
        assert "recommendations" in formatted_response

        assert formatted_response["episodes"] == []
        assert formatted_response["resources"] is None
        assert formatted_response["characters"] == []
        assert formatted_response["tags"] == []
        assert formatted_response["recommendations"] == []
