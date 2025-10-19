"""Data models for AniDB API responses.

This module contains Pydantic models for structured data representation
of anime information from the AniDB HTTP API.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class AnimeEpisode(BaseModel):
    """Model for individual anime episodes.

    Represents episode information including titles, air dates, and descriptions.
    """

    episode_number: int = Field(..., gt=0, description="Episode number")
    title: str | None = Field(None, max_length=500, description="Episode title")
    air_date: datetime | None = Field(None, description="Episode air date")
    description: str | None = Field(None, max_length=2000, description="Episode description")
    length: int | None = Field(None, gt=0, description="Episode duration in minutes")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Validate episode title if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate episode description if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class ExternalResource(BaseModel):
    """Model for external resource links.

    Represents links to external platforms and databases.
    """

    type: str = Field(..., min_length=1, max_length=50, description="Platform identifier")
    identifier: str | None = Field(None, max_length=100, description="External identifier")
    url: str | None = Field(None, max_length=500, description="External URL")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate resource type is not empty."""
        if not v or not v.strip():
            raise ValueError("Resource type cannot be empty")
        return v.strip()

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str | None) -> str | None:
        """Validate identifier if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Validate URL if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class AnimeResources(BaseModel):
    """Model for organizing external resources by platform.

    Groups external resources by platform type for easy access.
    """

    myanimelist: list[ExternalResource] = Field(
        default_factory=list, description="MyAnimeList resources"
    )
    imdb: list[ExternalResource] = Field(
        default_factory=list, description="IMDB resources"
    )
    official_sites: list[ExternalResource] = Field(
        default_factory=list, description="Official website resources"
    )
    other: list[ExternalResource] = Field(
        default_factory=list, description="Other external resources"
    )


class VoiceActor(BaseModel):
    """Model for voice actor information.

    Represents voice actors associated with anime characters.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Voice actor name")
    id: int | None = Field(None, gt=0, description="Voice actor ID in AniDB")
    language: str | None = Field(None, max_length=10, description="Voice acting language")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate voice actor name is not empty."""
        if not v or not v.strip():
            raise ValueError("Voice actor name cannot be empty")
        return v.strip()

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate language if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class AnimeCharacter(BaseModel):
    """Model for anime character information.

    Represents characters in anime with their descriptions and voice actors.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Character name")
    id: int | None = Field(None, gt=0, description="Character ID in AniDB")
    description: str | None = Field(None, max_length=2000, description="Character description")
    voice_actors: list[VoiceActor] = Field(
        default_factory=list, description="List of voice actors for this character"
    )
    character_type: str | None = Field(None, max_length=50, description="Character type (Main, Secondary, etc.)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate character name is not empty."""
        if not v or not v.strip():
            raise ValueError("Character name cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate character description if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("character_type")
    @classmethod
    def validate_character_type(cls, v: str | None) -> str | None:
        """Validate character type if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class AnimeTag(BaseModel):
    """Model for anime tags and genres.

    Represents AniDB's tag system for categorizing anime content.
    """

    id: int = Field(..., gt=0, description="Tag ID in AniDB")
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")
    description: str | None = Field(None, max_length=1000, description="Tag description")
    weight: int | None = Field(None, ge=0, le=600, description="Tag weight/relevance")
    spoiler: bool = Field(False, description="Whether tag contains spoilers")
    verified: bool = Field(False, description="Whether tag is verified")
    parent_id: int | None = Field(None, gt=0, description="Parent tag ID for hierarchies")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tag name is not empty."""
        if not v or not v.strip():
            raise ValueError("Tag name cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate tag description if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class AnimeRecommendation(BaseModel):
    """Model for user recommendations.

    Represents community recommendations and reviews for anime.
    """

    type: str = Field(..., min_length=1, max_length=50, description="Recommendation type")
    text: str = Field(..., min_length=1, max_length=2000, description="Recommendation text")
    user_id: int | None = Field(None, gt=0, description="User ID who made the recommendation")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate recommendation type is not empty."""
        if not v or not v.strip():
            raise ValueError("Recommendation type cannot be empty")
        return v.strip()

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate recommendation text is not empty."""
        if not v or not v.strip():
            raise ValueError("Recommendation text cannot be empty")
        return v.strip()


class AnimeSearchResult(BaseModel):
    """Model for anime search result entries.

    Represents basic anime information returned from search queries.
    """

    aid: int = Field(..., gt=0, description="AniDB anime ID")
    title: str = Field(..., min_length=1, max_length=500, description="Anime title")
    type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Anime type (TV, Movie, OVA, etc.)",
    )
    year: int | None = Field(None, ge=1900, le=2100, description="Release year")

    @field_validator("title", "type")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string fields are not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class AnimeTitle(BaseModel):
    """Model for anime title variations.

    Represents different title variations in various languages and types.
    """

    title: str = Field(..., min_length=1, max_length=500, description="Title text")
    language: str = Field(
        ..., min_length=2, max_length=10, description="Language code (e.g., 'en', 'ja')"
    )
    type: str = Field(..., description="Title type (main, official, synonym, short)")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_title_type(cls, v: str) -> str:
        """Validate title type is one of the allowed values."""
        allowed_types = {"main", "official", "synonym", "short", "titlecard"}
        if v.lower() not in allowed_types:
            raise ValueError(f"Title type must be one of: {', '.join(allowed_types)}")
        return v.lower()


class AnimeCreator(BaseModel):
    """Model for anime creators and staff.

    Represents people involved in anime production.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Creator name")
    id: int = Field(..., gt=0, description="Creator ID in AniDB")
    type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Role type (Direction, Music, etc.)",
    )

    @field_validator("name", "type")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string fields are not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class RelatedAnime(BaseModel):
    """Model for related anime entries.

    Represents anime that are related to the current anime (sequels, prequels, etc.).
    """

    aid: int = Field(..., gt=0, description="Related anime AniDB ID")
    title: str = Field(
        ..., min_length=1, max_length=500, description="Related anime title"
    )
    type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Relation type (Sequel, Prequel, etc.)",
    )

    @field_validator("title", "type")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string fields are not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class AnimeRatings(BaseModel):
    """Model for anime ratings from AniDB.

    Represents different types of ratings available for an anime.
    """

    permanent: float | None = Field(None, ge=0, le=10, description="Permanent rating")
    temporary: float | None = Field(None, ge=0, le=10, description="Temporary rating")
    review: float | None = Field(None, ge=0, le=10, description="Review rating")
    permanent_count: int | None = Field(None, ge=0, description="Number of permanent votes")
    temporary_count: int | None = Field(None, ge=0, description="Number of temporary votes")
    review_count: int | None = Field(None, ge=0, description="Number of review votes")


class SimilarAnime(BaseModel):
    """Model for similar anime entries.

    Represents anime that are similar to the current anime.
    """

    aid: int = Field(..., gt=0, description="Similar anime AniDB ID")
    title: str = Field(
        ..., min_length=1, max_length=500, description="Similar anime title"
    )
    approval: int | None = Field(None, ge=0, description="Number of approval votes")
    total: int | None = Field(None, ge=0, description="Total number of votes")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate that title is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()


class AnimeDetails(BaseModel):
    """Model for detailed anime information.

    Represents comprehensive anime data including metadata, creators, and related content.
    """

    aid: int = Field(..., gt=0, description="AniDB anime ID")
    title: str = Field(
        ..., min_length=1, max_length=500, description="Main anime title"
    )
    type: str = Field(..., min_length=1, max_length=50, description="Anime type")
    episode_count: int = Field(..., ge=0, description="Number of episodes")
    start_date: datetime | None = Field(None, description="Anime start date")
    end_date: datetime | None = Field(None, description="Anime end date")
    titles: list[AnimeTitle] = Field(
        default_factory=list, description="List of title variations"
    )
    synopsis: str | None = Field(None, max_length=5000, description="Anime synopsis")
    url: HttpUrl | None = Field(None, description="Official anime URL")
    creators: list[AnimeCreator] = Field(
        default_factory=list, description="List of creators and staff"
    )
    related_anime: list[RelatedAnime] = Field(
        default_factory=list, description="List of related anime"
    )
    restricted: bool = Field(
        False, description="Whether anime content is age-restricted"
    )
    ratings: AnimeRatings | None = Field(None, description="Anime ratings information")
    similar_anime: list[SimilarAnime] = Field(
        default_factory=list, description="List of similar anime"
    )
    picture: str | None = Field(None, description="Picture filename")
    
    # New enhanced fields
    episodes: list[AnimeEpisode] = Field(
        default_factory=list, description="List of episode information"
    )
    resources: AnimeResources | None = Field(None, description="External resource links")
    characters: list[AnimeCharacter] = Field(
        default_factory=list, description="List of anime characters"
    )
    tags: list[AnimeTag] = Field(
        default_factory=list, description="List of tags and genres"
    )
    recommendations: list[AnimeRecommendation] = Field(
        default_factory=list, description="List of user recommendations"
    )

    @field_validator("title", "type")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string fields are not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()

    @field_validator("synopsis")
    @classmethod
    def validate_synopsis(cls, v: str | None) -> str | None:
        """Validate synopsis if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime | None, info) -> datetime | None:
        """Validate that end_date is after start_date if both are provided."""
        if v is not None and "start_date" in info.data:
            start_date = info.data["start_date"]
            if start_date is not None and v < start_date:
                raise ValueError("End date cannot be before start date")
        return v


# Import APIError from exceptions module for backward compatibility
from .exceptions import APIError
