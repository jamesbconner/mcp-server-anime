"""MCP tools for anime data access.

This module implements the MCP tools that provide anime search and details
functionality to AI assistants through the Model Context Protocol.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from .core.error_handler import handle_mcp_tool_error
from .core.exceptions import APIError, DataValidationError
from .core.logging_config import get_logger, set_request_context
from .core.models import AnimeDetails, AnimeSearchResult
from .providers.anidb.config import load_config
from .providers.anidb.search_service import get_search_service
from .providers.anidb.service import create_anidb_service

logger = get_logger(__name__)


def register_anime_tools(mcp: FastMCP) -> None:
    """Register all anime-related MCP tools.

    Args:
        mcp: FastMCP server instance to register tools with

    Example:
        >>> from mcp.server.fastmcp import FastMCP
        >>> mcp = FastMCP("anime-server")
        >>> register_anime_tools(mcp)
    """

    @mcp.tool()
    async def anidb_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for anime by title using AniDB local database.

        Search the AniDB database for anime matching the provided query string.
        Uses a local database for fast response times and reduced API dependency.
        Returns basic information about matching anime including title, type, and year.

        Data Source: AniDB (https://anidb.net)

        Args:
            query: Search term for anime title (minimum 2 characters)
            limit: Maximum number of results to return (default: 10, max: 20)

        Returns:
            List of anime search results with basic information from AniDB

        Raises:
            ValueError: If query is too short or limit is invalid
            RuntimeError: If the local database is not available or search fails

        Example:
            >>> results = await anidb_search("evangelion", limit=5)
            >>> for result in results:
            ...     print(f"{result['title']} ({result['year']})")
        """
        set_request_context(operation="anidb_search_tool")
        logger.info(
            "AniDB search tool requested",
            query=query,
            limit=limit,
        )

        try:
            # Validate parameters
            if not query or not query.strip():
                raise DataValidationError(
                    "Search query cannot be empty",
                    field_name="query",
                    field_value=query,
                )

            if len(query.strip()) < 2:
                raise DataValidationError(
                    "Search query must be at least 2 characters long",
                    field_name="query",
                    field_value=query,
                )

            if limit < 1:
                raise DataValidationError(
                    "Limit must be at least 1",
                    field_name="limit",
                    field_value=limit,
                )

            if limit > 20:
                raise DataValidationError(
                    "Limit cannot exceed 20 for MCP tool usage",
                    field_name="limit",
                    field_value=limit,
                )

            # Use local search service for fast database-based search
            search_service = get_search_service()

            # Generate client ID for transaction tracking (use "mcp_tool" as identifier)
            client_id = "mcp_tool"

            results = await search_service.search_anime(
                query.strip(), limit, client_id=client_id
            )

            # Format results for MCP response
            formatted_results = []
            for result in results:
                formatted_result = {
                    "aid": result.aid,
                    "title": result.title,
                    "type": result.type,
                    "year": result.year,
                }
                formatted_results.append(formatted_result)

            logger.info(
                "AniDB search tool completed",
                query=query,
                limit=limit,
                result_count=len(formatted_results),
            )
            return formatted_results

        except Exception as e:
            # Handle and convert errors for MCP
            mcp_error = handle_mcp_tool_error(
                e, "anidb_search", {"query": query, "limit": limit}
            )

            # Convert to appropriate MCP exceptions
            if isinstance(e, DataValidationError):
                raise ValueError(f"{e.message}: {e.details or ''}") from e
            else:
                raise RuntimeError(f"AniDB search failed: {e}") from e

    @mcp.tool()
    async def anidb_details(aid: int) -> dict[str, Any]:
        """Get detailed information about a specific anime from AniDB.

        Retrieve comprehensive anime data from AniDB including synopsis, ratings,
        episode count, air dates, creators, related anime information, and enhanced
        data such as episodes, external resources, characters, tags, and recommendations.

        Data Source: AniDB (https://anidb.net)

        Args:
            aid: AniDB anime ID (must be a positive integer)

        Returns:
            Dictionary containing detailed anime information from AniDB with the following structure:
            - Basic fields: aid, title, type, episode_count, start_date, end_date, synopsis, etc.
            - Enhanced fields:
                - episodes: List of episode information with titles, air dates, and descriptions
                - resources: External links to MyAnimeList, IMDB, official sites, etc.
                - characters: Character information with voice actors
                - tags: Genre and content tags with weights and spoiler flags
                - recommendations: User recommendations and reviews

        Raises:
            ValueError: If anime ID is invalid
            RuntimeError: If the API request fails or anime is not found

        Example:
            >>> details = await anidb_details(30)
            >>> print(f"{details['title']} - {details['episode_count']} episodes")
            >>> print(f"Episodes available: {len(details['episodes'])}")
            >>> print(f"Characters: {len(details['characters'])}")
            >>> if details['resources']:
            ...     print(f"MyAnimeList entries: {len(details['resources']['myanimelist'])}")
        """
        set_request_context(operation="anidb_details_tool")
        logger.info(
            "AniDB details tool requested",
            aid=aid,
        )

        try:
            # Validate anime ID parameter
            if not isinstance(aid, int):
                raise DataValidationError(
                    f"Anime ID must be an integer, got {type(aid).__name__}",
                    field_name="aid",
                    field_value=aid,
                )

            if aid < 1:
                raise DataValidationError(
                    f"Anime ID must be a positive integer, got {aid}",
                    field_name="aid",
                    field_value=aid,
                )

            if aid > 999999:
                raise DataValidationError(
                    f"Anime ID appears to be out of valid range (1-999999), got {aid}",
                    field_name="aid",
                    field_value=aid,
                )

            # Create service and get anime details
            config = load_config()
            service = await create_anidb_service(config)
            async with service:
                details = await service.get_anime_details(aid)

                # Format details for MCP response
                formatted_details = _format_anime_details(details)

                logger.info(
                    "AniDB details tool completed",
                    aid=aid,
                    title=details.title,
                    episode_count=details.episode_count,
                )
                return formatted_details

        except Exception as e:
            # Handle and convert errors for MCP
            mcp_error = handle_mcp_tool_error(e, "anidb_details", {"aid": aid})

            # Convert to appropriate MCP exceptions
            if isinstance(e, DataValidationError):
                raise ValueError(f"{e.message}: {e.details or ''}") from e
            elif isinstance(e, APIError) and e.code == "ANIME_NOT_FOUND":
                raise RuntimeError(f"Anime not found: {e.message}") from e
            else:
                raise RuntimeError(f"AniDB details fetch failed: {e}") from e


def _format_anime_details(details: AnimeDetails) -> dict[str, Any]:
    """Format AnimeDetails for MCP response.

    Args:
        details: AnimeDetails object to format

    Returns:
        Dictionary representation suitable for MCP response
    """
    # Format dates as ISO strings if present
    start_date = details.start_date.isoformat() if details.start_date else None
    end_date = details.end_date.isoformat() if details.end_date else None

    # Format titles list
    titles = []
    for title in details.titles:
        titles.append(
            {"title": title.title, "language": title.language, "type": title.type}
        )

    # Format creators list
    creators = []
    for creator in details.creators:
        creators.append({"name": creator.name, "id": creator.id, "type": creator.type})

    # Format related anime list
    related_anime = []
    for related in details.related_anime:
        related_anime.append(
            {"aid": related.aid, "title": related.title, "type": related.type}
        )

    # Format ratings
    ratings = None
    if details.ratings:
        ratings = {
            "permanent": details.ratings.permanent,
            "temporary": details.ratings.temporary,
            "review": details.ratings.review,
            "permanent_count": details.ratings.permanent_count,
            "temporary_count": details.ratings.temporary_count,
            "review_count": details.ratings.review_count,
        }

    # Format similar anime list
    similar_anime = []
    for similar in details.similar_anime:
        similar_anime.append(
            {
                "aid": similar.aid,
                "title": similar.title,
                "approval": similar.approval,
                "total": similar.total,
            }
        )

    # Format episodes list
    episodes = []
    for episode in details.episodes:
        episode_data = {
            "episode_number": episode.episode_number,
            "title": episode.title,
            "air_date": episode.air_date.isoformat() if episode.air_date else None,
            "description": episode.description,
            "length": episode.length,
        }
        episodes.append(episode_data)

    # Format resources
    resources = None
    if details.resources:
        resources = {
            "myanimelist": [
                {
                    "type": res.type,
                    "identifier": res.identifier,
                    "url": res.url,
                }
                for res in details.resources.myanimelist
            ],
            "imdb": [
                {
                    "type": res.type,
                    "identifier": res.identifier,
                    "url": res.url,
                }
                for res in details.resources.imdb
            ],
            "official_sites": [
                {
                    "type": res.type,
                    "identifier": res.identifier,
                    "url": res.url,
                }
                for res in details.resources.official_sites
            ],
            "other": [
                {
                    "type": res.type,
                    "identifier": res.identifier,
                    "url": res.url,
                }
                for res in details.resources.other
            ],
        }

    # Format characters list
    characters = []
    for character in details.characters:
        voice_actors = [
            {
                "name": va.name,
                "id": va.id,
                "language": va.language,
            }
            for va in character.voice_actors
        ]

        character_data = {
            "name": character.name,
            "id": character.id,
            "description": character.description,
            "voice_actors": voice_actors,
            "character_type": character.character_type,
        }
        characters.append(character_data)

    # Format tags list
    tags = []
    for tag in details.tags:
        tag_data = {
            "id": tag.id,
            "name": tag.name,
            "description": tag.description,
            "weight": tag.weight,
            "spoiler": tag.spoiler,
            "verified": tag.verified,
            "parent_id": tag.parent_id,
        }
        tags.append(tag_data)

    # Format recommendations list
    recommendations = []
    for recommendation in details.recommendations:
        rec_data = {
            "type": recommendation.type,
            "text": recommendation.text,
            "user_id": recommendation.user_id,
        }
        recommendations.append(rec_data)

    return {
        "aid": details.aid,
        "title": details.title,
        "type": details.type,
        "episode_count": details.episode_count,
        "start_date": start_date,
        "end_date": end_date,
        "titles": titles,
        "synopsis": details.synopsis,
        "url": str(details.url) if details.url else None,
        "creators": creators,
        "related_anime": related_anime,
        "restricted": details.restricted,
        "ratings": ratings,
        "similar_anime": similar_anime,
        "picture": details.picture,
        # Enhanced fields
        "episodes": episodes,
        "resources": resources,
        "characters": characters,
        "tags": tags,
        "recommendations": recommendations,
    }


def _format_anime_search_result(result: AnimeSearchResult) -> dict[str, Any]:
    """Format an AnimeSearchResult for MCP response.

    Args:
        result: AnimeSearchResult object to format

    Returns:
        Dictionary representation suitable for MCP response
    """
    return {
        "aid": result.aid,
        "title": result.title,
        "type": result.type,
        "year": result.year,
    }


def _validate_search_parameters(query: str, limit: int) -> None:
    """Validate anime search parameters.

    Args:
        query: Search query string
        limit: Result limit

    Raises:
        ValueError: If parameters are invalid
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if len(query.strip()) < 2:
        raise ValueError("Search query must be at least 2 characters long")

    if limit < 1:
        raise ValueError("Limit must be at least 1")

    if limit > 20:
        raise ValueError("Limit cannot exceed 20 for MCP tool usage")
