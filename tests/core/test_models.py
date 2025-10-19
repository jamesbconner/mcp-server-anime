"""Unit tests for data models.

Tests validation, serialization, and deserialization of Pydantic models
used for AniDB API responses.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.mcp_server_anime.core.models import (
    AnimeCreator,
    AnimeDetails,
    AnimeSearchResult,
    AnimeTitle,
    APIError,
    RelatedAnime,
)


class TestAnimeSearchResult:
    """Test cases for AnimeSearchResult model."""

    def test_valid_anime_search_result(self):
        """Test creating a valid AnimeSearchResult."""
        result = AnimeSearchResult(aid=123, title="Test Anime", type="TV", year=2023)

        assert result.aid == 123
        assert result.title == "Test Anime"
        assert result.type == "TV"
        assert result.year == 2023

    def test_anime_search_result_without_year(self):
        """Test creating AnimeSearchResult without optional year."""
        result = AnimeSearchResult(aid=456, title="Another Anime", type="Movie")

        assert result.aid == 456
        assert result.title == "Another Anime"
        assert result.type == "Movie"
        assert result.year is None

    def test_invalid_aid_zero(self):
        """Test that aid must be greater than 0."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeSearchResult(aid=0, title="Test", type="TV")

        assert "greater than 0" in str(exc_info.value)

    def test_invalid_aid_negative(self):
        """Test that aid cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeSearchResult(aid=-1, title="Test", type="TV")

        assert "greater than 0" in str(exc_info.value)

    def test_empty_title(self):
        """Test that title cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeSearchResult(aid=123, title="", type="TV")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_title(self):
        """Test that title cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeSearchResult(aid=123, title="   ", type="TV")

        assert "cannot be empty" in str(exc_info.value)

    def test_title_trimming(self):
        """Test that title is trimmed of whitespace."""
        result = AnimeSearchResult(aid=123, title="  Test Anime  ", type="TV")
        assert result.title == "Test Anime"

    def test_invalid_year_range(self):
        """Test year validation range."""
        with pytest.raises(ValidationError):
            AnimeSearchResult(aid=123, title="Test", type="TV", year=1800)

        with pytest.raises(ValidationError):
            AnimeSearchResult(aid=123, title="Test", type="TV", year=2200)

    def test_serialization(self):
        """Test model serialization to dict."""
        result = AnimeSearchResult(aid=123, title="Test", type="TV", year=2023)
        data = result.model_dump()

        expected = {"aid": 123, "title": "Test", "type": "TV", "year": 2023}
        assert data == expected


class TestAnimeTitle:
    """Test cases for AnimeTitle model."""

    def test_valid_anime_title(self):
        """Test creating a valid AnimeTitle."""
        title = AnimeTitle(title="Attack on Titan", language="en", type="main")

        assert title.title == "Attack on Titan"
        assert title.language == "en"
        assert title.type == "main"

    def test_title_type_validation(self):
        """Test that title type is validated against allowed values."""
        # Valid types
        for title_type in ["main", "official", "synonym", "short"]:
            title = AnimeTitle(title="Test", language="en", type=title_type)
            assert title.type == title_type

    def test_invalid_title_type(self):
        """Test that invalid title types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeTitle(title="Test", language="en", type="invalid")

        assert "must be one of" in str(exc_info.value)

    def test_title_type_case_insensitive(self):
        """Test that title type validation is case insensitive."""
        title = AnimeTitle(title="Test", language="en", type="MAIN")
        assert title.type == "main"

    def test_empty_title_validation(self):
        """Test that title cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeTitle(title="", language="en", type="main")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_title_validation(self):
        """Test that title cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeTitle(title="   ", language="en", type="main")

        assert "cannot be empty" in str(exc_info.value)

    def test_title_trimming(self):
        """Test that title is trimmed of whitespace."""
        title = AnimeTitle(title="  Attack on Titan  ", language="en", type="main")
        assert title.title == "Attack on Titan"

    def test_language_validation(self):
        """Test language field validation."""
        # Valid language codes
        title = AnimeTitle(title="Test", language="ja", type="main")
        assert title.language == "ja"

        # Short language code
        title = AnimeTitle(title="Test", language="zh", type="main")
        assert title.language == "zh"

    def test_edge_case_title_lengths(self):
        """Test edge cases for title length validation."""
        # Single character title
        title = AnimeTitle(title="A", language="en", type="main")
        assert title.title == "A"

        # Very long title (within limit)
        long_title = "A" * 500
        title = AnimeTitle(title=long_title, language="en", type="main")
        assert title.title == long_title


class TestAnimeCreator:
    """Test cases for AnimeCreator model."""

    def test_valid_anime_creator(self):
        """Test creating a valid AnimeCreator."""
        creator = AnimeCreator(name="Hayao Miyazaki", id=12345, type="Direction")

        assert creator.name == "Hayao Miyazaki"
        assert creator.id == 12345
        assert creator.type == "Direction"

    def test_invalid_creator_id(self):
        """Test that creator ID must be positive."""
        with pytest.raises(ValidationError):
            AnimeCreator(name="Test", id=0, type="Direction")

        with pytest.raises(ValidationError):
            AnimeCreator(name="Test", id=-1, type="Direction")

    def test_empty_name_validation(self):
        """Test that name cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeCreator(name="", id=123, type="Direction")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_name_validation(self):
        """Test that name cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeCreator(name="   ", id=123, type="Direction")

        assert "cannot be empty" in str(exc_info.value)

    def test_empty_type_validation(self):
        """Test that type cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeCreator(name="Test", id=123, type="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_type_validation(self):
        """Test that type cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeCreator(name="Test", id=123, type="   ")

        assert "cannot be empty" in str(exc_info.value)

    def test_name_trimming(self):
        """Test that name is trimmed of whitespace."""
        creator = AnimeCreator(name="  Test Creator  ", id=123, type="Direction")
        assert creator.name == "Test Creator"

    def test_type_trimming(self):
        """Test that type is trimmed of whitespace."""
        creator = AnimeCreator(name="Test", id=123, type="  Direction  ")
        assert creator.type == "Direction"

    def test_various_creator_types(self):
        """Test various creator types."""
        types = ["Direction", "Music", "Animation", "Character Design", "Script"]
        for creator_type in types:
            creator = AnimeCreator(name="Test", id=123, type=creator_type)
            assert creator.type == creator_type


class TestRelatedAnime:
    """Test cases for RelatedAnime model."""

    def test_valid_related_anime(self):
        """Test creating a valid RelatedAnime."""
        related = RelatedAnime(aid=456, title="Sequel Anime", type="Sequel")

        assert related.aid == 456
        assert related.title == "Sequel Anime"
        assert related.type == "Sequel"

    def test_invalid_aid(self):
        """Test that aid must be positive."""
        with pytest.raises(ValidationError):
            RelatedAnime(aid=0, title="Test", type="Sequel")

        with pytest.raises(ValidationError):
            RelatedAnime(aid=-1, title="Test", type="Sequel")

    def test_empty_title_validation(self):
        """Test that title cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            RelatedAnime(aid=123, title="", type="Sequel")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_title_validation(self):
        """Test that title cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            RelatedAnime(aid=123, title="   ", type="Sequel")

        assert "cannot be empty" in str(exc_info.value)

    def test_empty_type_validation(self):
        """Test that type cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            RelatedAnime(aid=123, title="Test", type="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_type_validation(self):
        """Test that type cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            RelatedAnime(aid=123, title="Test", type="   ")

        assert "cannot be empty" in str(exc_info.value)

    def test_title_and_type_trimming(self):
        """Test that title and type are trimmed of whitespace."""
        related = RelatedAnime(aid=123, title="  Test Anime  ", type="  Sequel  ")
        assert related.title == "Test Anime"
        assert related.type == "Sequel"

    def test_various_relation_types(self):
        """Test various relation types."""
        types = ["Sequel", "Prequel", "Side Story", "Alternative Version", "Summary"]
        for relation_type in types:
            related = RelatedAnime(aid=123, title="Test", type=relation_type)
            assert related.type == relation_type


class TestAnimeDetails:
    """Test cases for AnimeDetails model."""

    def test_valid_anime_details_minimal(self):
        """Test creating AnimeDetails with minimal required fields."""
        details = AnimeDetails(aid=123, title="Test Anime", type="TV", episode_count=12)

        assert details.aid == 123
        assert details.title == "Test Anime"
        assert details.type == "TV"
        assert details.episode_count == 12
        assert details.start_date is None
        assert details.end_date is None
        assert details.titles == []
        assert details.synopsis is None
        assert details.url is None
        assert details.creators == []
        assert details.related_anime == []
        assert details.restricted is False

    def test_valid_anime_details_complete(self):
        """Test creating AnimeDetails with all fields."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)

        titles = [
            AnimeTitle(title="Test Anime", language="en", type="main"),
            AnimeTitle(title="テストアニメ", language="ja", type="official"),
        ]

        creators = [
            AnimeCreator(name="Director Name", id=123, type="Direction"),
            AnimeCreator(name="Composer Name", id=456, type="Music"),
        ]

        related = [RelatedAnime(aid=789, title="Prequel", type="Prequel")]

        details = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="TV",
            episode_count=24,
            start_date=start_date,
            end_date=end_date,
            titles=titles,
            synopsis="A test anime synopsis.",
            url="https://example.com/anime",
            creators=creators,
            related_anime=related,
            restricted=True,
        )

        assert details.aid == 123
        assert details.title == "Test Anime"
        assert details.episode_count == 24
        assert details.start_date == start_date
        assert details.end_date == end_date
        assert len(details.titles) == 2
        assert len(details.creators) == 2
        assert len(details.related_anime) == 1
        assert details.restricted is True

    def test_invalid_episode_count(self):
        """Test that episode count cannot be negative."""
        with pytest.raises(ValidationError):
            AnimeDetails(aid=123, title="Test", type="TV", episode_count=-1)

    def test_date_validation(self):
        """Test that end_date cannot be before start_date."""
        start_date = datetime(2023, 3, 31)
        end_date = datetime(2023, 1, 1)  # Before start_date

        with pytest.raises(ValidationError) as exc_info:
            AnimeDetails(
                aid=123,
                title="Test",
                type="TV",
                episode_count=12,
                start_date=start_date,
                end_date=end_date,
            )

        assert "cannot be before start date" in str(exc_info.value)

    def test_synopsis_trimming(self):
        """Test that synopsis is trimmed and empty strings become None."""
        # Non-empty synopsis
        details1 = AnimeDetails(
            aid=123,
            title="Test",
            type="TV",
            episode_count=12,
            synopsis="  A good synopsis.  ",
        )
        assert details1.synopsis == "A good synopsis."

        # Empty synopsis becomes None
        details2 = AnimeDetails(
            aid=123, title="Test", type="TV", episode_count=12, synopsis="   "
        )
        assert details2.synopsis is None

    def test_invalid_url(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError):
            AnimeDetails(
                aid=123,
                title="Test",
                type="TV",
                episode_count=12,
                url="not-a-valid-url",
            )

    def test_empty_title_validation(self):
        """Test that title cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeDetails(aid=123, title="", type="TV", episode_count=12)

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_title_validation(self):
        """Test that title cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeDetails(aid=123, title="   ", type="TV", episode_count=12)

        assert "cannot be empty" in str(exc_info.value)

    def test_empty_type_validation(self):
        """Test that type cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeDetails(aid=123, title="Test", type="", episode_count=12)

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_type_validation(self):
        """Test that type cannot be whitespace only."""
        with pytest.raises(ValidationError) as exc_info:
            AnimeDetails(aid=123, title="Test", type="   ", episode_count=12)

        assert "cannot be empty" in str(exc_info.value)

    def test_title_and_type_trimming(self):
        """Test that title and type are trimmed of whitespace."""
        details = AnimeDetails(
            aid=123, title="  Test Anime  ", type="  TV  ", episode_count=12
        )
        assert details.title == "Test Anime"
        assert details.type == "TV"

    def test_zero_episode_count(self):
        """Test that episode count can be zero."""
        details = AnimeDetails(aid=123, title="Test", type="TV", episode_count=0)
        assert details.episode_count == 0

    def test_large_episode_count(self):
        """Test handling of large episode counts."""
        details = AnimeDetails(aid=123, title="Test", type="TV", episode_count=9999)
        assert details.episode_count == 9999

    def test_complex_nested_validation(self):
        """Test validation with complex nested objects."""
        # Test with invalid nested AnimeTitle
        with pytest.raises(ValidationError):
            AnimeDetails(
                aid=123,
                title="Test",
                type="TV",
                episode_count=12,
                titles=[
                    AnimeTitle(
                        title="", language="en", type="main"
                    )  # Invalid empty title
                ],
            )

        # Test with invalid nested AnimeCreator
        with pytest.raises(ValidationError):
            AnimeDetails(
                aid=123,
                title="Test",
                type="TV",
                episode_count=12,
                creators=[
                    AnimeCreator(name="Test", id=0, type="Direction")  # Invalid ID
                ],
            )

        # Test with invalid nested RelatedAnime
        with pytest.raises(ValidationError):
            AnimeDetails(
                aid=123,
                title="Test",
                type="TV",
                episode_count=12,
                related_anime=[
                    RelatedAnime(aid=-1, title="Test", type="Sequel")  # Invalid ID
                ],
            )

    def test_synopsis_edge_cases(self):
        """Test synopsis validation edge cases."""
        # Empty string synopsis becomes None
        details = AnimeDetails(
            aid=123, title="Test", type="TV", episode_count=12, synopsis=""
        )
        assert details.synopsis is None

        # Whitespace-only synopsis becomes None
        details = AnimeDetails(
            aid=123, title="Test", type="TV", episode_count=12, synopsis="   \n\t  "
        )
        assert details.synopsis is None

        # Synopsis with leading/trailing whitespace is trimmed
        details = AnimeDetails(
            aid=123,
            title="Test",
            type="TV",
            episode_count=12,
            synopsis="  A great anime story.  ",
        )
        assert details.synopsis == "A great anime story."

    def test_date_edge_cases(self):
        """Test date validation edge cases."""
        # Same start and end date should be valid
        same_date = datetime(2023, 1, 1)
        details = AnimeDetails(
            aid=123,
            title="Test",
            type="TV",
            episode_count=12,
            start_date=same_date,
            end_date=same_date,
        )
        assert details.start_date == same_date
        assert details.end_date == same_date

        # End date exactly one day after start date
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        details = AnimeDetails(
            aid=123,
            title="Test",
            type="TV",
            episode_count=12,
            start_date=start_date,
            end_date=end_date,
        )
        assert details.start_date == start_date
        assert details.end_date == end_date


class TestAPIError:
    """Test cases for APIError model."""

    def test_valid_api_error(self):
        """Test creating a valid APIError."""
        error = APIError(
            "Anime not found",
            code="NOT_FOUND",
            details="The requested anime ID does not exist",
        )

        assert error.code == "NOT_FOUND"
        assert error.message == "Anime not found"
        assert error.details == "The requested anime ID does not exist"

    def test_api_error_without_details(self):
        """Test creating APIError without optional details."""
        error = APIError("Rate limit exceeded", code="RATE_LIMIT")

        assert error.code == "RATE_LIMIT"
        assert error.message == "Rate limit exceeded"
        assert error.details is None

    def test_empty_code_validation(self):
        """Test that code defaults to class name when empty."""
        # When code is empty string, it defaults to class name in uppercase
        error = APIError("Test message", code="")
        assert error.code == "APIERROR"  # Defaults to class name when empty
        assert error.message == "Test message"

    def test_empty_message_validation(self):
        """Test that message can be empty (no validation in Exception class)."""
        # APIError is now an Exception, so it accepts any string values
        error = APIError("", code="TEST")
        assert error.code == "TEST"
        assert error.message == ""

    def test_details_handling(self):
        """Test that details are stored as provided."""
        # Non-empty details
        error1 = APIError("Test", code="TEST", details="  Some details.  ")
        assert error1.details == "  Some details.  "

        # Empty details remain as provided
        error2 = APIError("Test", code="TEST", details="   ")
        assert error2.details == "   "

        # None details
        error3 = APIError("Test", code="TEST", details=None)
        assert error3.details is None

    def test_field_storage(self):
        """Test that string fields are stored as provided."""
        error = APIError("  Test message  ", code="  TEST_CODE  ")

        assert error.code == "  TEST_CODE  "
        assert error.message == "  Test message  "

    def test_string_representation(self):
        """Test string representation of APIError."""
        # Error without details
        error1 = APIError("Test message", code="TEST")
        assert str(error1) == "TEST: Test message"

        # Error with details
        error2 = APIError("Test message", code="TEST", details="Additional info")
        assert str(error2) == "TEST: Test message | Details: Additional info"

    def test_repr_representation(self):
        """Test repr representation of APIError."""
        error = APIError("Test message", code="TEST", details="Additional info")
        expected = "APIError(message='Test message', code='TEST', details='Additional info', context={})"
        assert repr(error) == expected


class TestModelSerialization:
    """Test serialization and deserialization of models."""

    def test_anime_details_json_serialization(self):
        """Test that AnimeDetails can be serialized to and from JSON."""
        original = AnimeDetails(
            aid=123,
            title="Test Anime",
            type="TV",
            episode_count=12,
            start_date=datetime(2023, 1, 1),
            titles=[AnimeTitle(title="Test", language="en", type="main")],
            creators=[AnimeCreator(name="Test Creator", id=456, type="Direction")],
        )

        # Serialize to dict
        data = original.model_dump()
        assert isinstance(data, dict)
        assert data["aid"] == 123
        assert data["title"] == "Test Anime"

        # Deserialize from dict
        restored = AnimeDetails.model_validate(data)
        assert restored.aid == original.aid
        assert restored.title == original.title
        assert len(restored.titles) == 1
        assert len(restored.creators) == 1

    def test_anime_search_result_serialization(self):
        """Test AnimeSearchResult serialization and deserialization."""
        original = AnimeSearchResult(aid=123, title="Test", type="TV", year=2023)

        # Serialize to dict
        data = original.model_dump()
        expected = {"aid": 123, "title": "Test", "type": "TV", "year": 2023}
        assert data == expected

        # Deserialize from dict
        restored = AnimeSearchResult.model_validate(data)
        assert restored.aid == original.aid
        assert restored.title == original.title
        assert restored.type == original.type
        assert restored.year == original.year

    def test_anime_title_serialization(self):
        """Test AnimeTitle serialization and deserialization."""
        original = AnimeTitle(title="Test", language="en", type="main")

        # Serialize to dict
        data = original.model_dump()
        expected = {"title": "Test", "language": "en", "type": "main"}
        assert data == expected

        # Deserialize from dict
        restored = AnimeTitle.model_validate(data)
        assert restored.title == original.title
        assert restored.language == original.language
        assert restored.type == original.type

    def test_anime_creator_serialization(self):
        """Test AnimeCreator serialization and deserialization."""
        original = AnimeCreator(name="Test Creator", id=123, type="Direction")

        # Serialize to dict
        data = original.model_dump()
        expected = {"name": "Test Creator", "id": 123, "type": "Direction"}
        assert data == expected

        # Deserialize from dict
        restored = AnimeCreator.model_validate(data)
        assert restored.name == original.name
        assert restored.id == original.id
        assert restored.type == original.type

    def test_related_anime_serialization(self):
        """Test RelatedAnime serialization and deserialization."""
        original = RelatedAnime(aid=456, title="Sequel", type="Sequel")

        # Serialize to dict
        data = original.model_dump()
        expected = {"aid": 456, "title": "Sequel", "type": "Sequel"}
        assert data == expected

        # Deserialize from dict
        restored = RelatedAnime.model_validate(data)
        assert restored.aid == original.aid
        assert restored.title == original.title
        assert restored.type == original.type

    def test_complex_anime_details_serialization(self):
        """Test complex AnimeDetails with all fields serialization."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)

        original = AnimeDetails(
            aid=123,
            title="Complex Anime",
            type="TV",
            episode_count=24,
            start_date=start_date,
            end_date=end_date,
            titles=[
                AnimeTitle(title="Complex Anime", language="en", type="main"),
                AnimeTitle(
                    title="コンプレックスアニメ", language="ja", type="official"
                ),
            ],
            synopsis="A complex anime with multiple elements.",
            url="https://example.com/anime",
            creators=[
                AnimeCreator(name="Director", id=123, type="Direction"),
                AnimeCreator(name="Composer", id=456, type="Music"),
            ],
            related_anime=[RelatedAnime(aid=789, title="Prequel", type="Prequel")],
            restricted=True,
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["aid"] == 123
        assert data["title"] == "Complex Anime"
        assert len(data["titles"]) == 2
        assert len(data["creators"]) == 2
        assert len(data["related_anime"]) == 1
        assert data["restricted"] is True

        # Deserialize from dict
        restored = AnimeDetails.model_validate(data)
        assert restored.aid == original.aid
        assert restored.title == original.title
        assert len(restored.titles) == 2
        assert len(restored.creators) == 2
        assert len(restored.related_anime) == 1
        assert restored.restricted == original.restricted

    def test_model_json_schema(self):
        """Test that models can generate JSON schemas."""
        schema = AnimeDetails.model_json_schema()

        assert "properties" in schema
        assert "aid" in schema["properties"]
        assert "title" in schema["properties"]
        assert "episode_count" in schema["properties"]

    def test_model_validation_from_partial_data(self):
        """Test model validation from partial data."""
        # Test with minimal required fields
        minimal_data = {"aid": 123, "title": "Test", "type": "TV", "episode_count": 12}

        details = AnimeDetails.model_validate(minimal_data)
        assert details.aid == 123
        assert details.title == "Test"
        assert details.type == "TV"
        assert details.episode_count == 12
        assert details.titles == []
        assert details.creators == []
        assert details.related_anime == []
        assert details.restricted is False

    def test_model_validation_with_extra_fields(self):
        """Test model validation ignores extra fields by default."""
        data_with_extra = {
            "aid": 123,
            "title": "Test",
            "type": "TV",
            "episode_count": 12,
            "extra_field": "should be ignored",
        }

        details = AnimeDetails.model_validate(data_with_extra)
        assert details.aid == 123
        assert details.title == "Test"
        assert not hasattr(details, "extra_field")
