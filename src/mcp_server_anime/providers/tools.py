"""Dynamic tool registration for anime data providers.

This module implements the dynamic MCP tool registration system that creates
provider-specific tools with consistent naming conventions across different
anime data providers.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.error_handler import handle_mcp_tool_error
from ..core.exceptions import DataValidationError, ProviderError
from ..core.logging_config import get_logger, set_request_context
from ..core.models import AnimeDetails
from .base import AnimeDataProvider
from .registry import ProviderRegistry

logger = get_logger(__name__)


class ToolNamingConvention:
    """Defines consistent naming conventions for MCP tools across providers.

    This class provides methods to generate standardized tool names that include
    the provider name to avoid conflicts when multiple providers are registered.
    """

    @staticmethod
    def search_tool_name(provider_name: str) -> str:
        """Generate tool name for anime search functionality.

        Args:
            provider_name: Name of the provider

        Returns:
            Standardized tool name for search functionality
        """
        return f"anime_search_{provider_name}"

    @staticmethod
    def details_tool_name(provider_name: str) -> str:
        """Generate tool name for anime details functionality.

        Args:
            provider_name: Name of the provider

        Returns:
            Standardized tool name for details functionality
        """
        return f"anime_details_{provider_name}"

    @staticmethod
    def recommendations_tool_name(provider_name: str) -> str:
        """Generate tool name for anime recommendations functionality.

        Args:
            provider_name: Name of the provider

        Returns:
            Standardized tool name for recommendations functionality
        """
        return f"anime_recommendations_{provider_name}"

    @staticmethod
    def seasonal_tool_name(provider_name: str) -> str:
        """Generate tool name for seasonal anime functionality.

        Args:
            provider_name: Name of the provider

        Returns:
            Standardized tool name for seasonal functionality
        """
        return f"anime_seasonal_{provider_name}"

    @staticmethod
    def trending_tool_name(provider_name: str) -> str:
        """Generate tool name for trending anime functionality.

        Args:
            provider_name: Name of the provider

        Returns:
            Standardized tool name for trending functionality
        """
        return f"anime_trending_{provider_name}"

    @staticmethod
    def parse_tool_name(tool_name: str) -> tuple[str, str] | None:
        """Parse a tool name to extract operation and provider.

        Args:
            tool_name: The tool name to parse

        Returns:
            Tuple of (operation, provider_name) if valid, None otherwise
        """
        if not tool_name.startswith("anime_"):
            return None

        parts = tool_name.split("_")
        if len(parts) < 3:
            return None

        operation = "_".join(parts[1:-1])  # Everything between "anime_" and provider
        provider_name = parts[-1]

        return operation, provider_name


def create_search_tool(
    mcp: FastMCP, provider: AnimeDataProvider, tool_name: str
) -> None:
    """Create and register a search tool for a specific provider.

    Args:
        mcp: FastMCP server instance
        provider: The anime data provider
        tool_name: Name for the tool
    """
    provider_name = provider.info.name
    display_name = provider.info.display_name
    max_results = provider.info.capabilities.max_search_results
    min_length = provider.info.capabilities.min_search_length

    @mcp.tool(name=tool_name)
    async def provider_search_tool(query: str, limit: int = 10) -> list[dict[str, Any]]:
        f"""Search for anime by title using {display_name}.

        Search the {display_name} database for anime matching the provided query string.
        Returns basic information about matching anime including title, type, and year.

        Args:
            query: Search term for anime title (minimum {min_length} characters)
            limit: Maximum number of results to return (default: 10, max: {max_results})

        Returns:
            List of anime search results with basic information

        Raises:
            ValueError: If query is too short or limit is invalid
            RuntimeError: If the API request fails
        """
        set_request_context(operation=f"{tool_name}_tool")
        logger.info(
            f"{display_name} search tool requested",
            provider=provider_name,
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

            if len(query.strip()) < min_length:
                raise DataValidationError(
                    f"Search query must be at least {min_length} characters long",
                    field_name="query",
                    field_value=query,
                )

            if limit < 1:
                raise DataValidationError(
                    "Limit must be at least 1",
                    field_name="limit",
                    field_value=limit,
                )

            if limit > max_results:
                raise DataValidationError(
                    f"Limit cannot exceed {max_results} for {display_name}",
                    field_name="limit",
                    field_value=limit,
                )

            # Perform search using the provider
            results = await provider.search_anime(query.strip(), limit)

            # Format results for MCP response
            formatted_results = []
            for result in results:
                formatted_result = {
                    "aid": result.aid,
                    "title": result.title,
                    "type": result.type,
                    "year": result.year,
                    "provider": provider_name,
                }
                formatted_results.append(formatted_result)

            logger.info(
                f"{display_name} search tool completed",
                provider=provider_name,
                query=query,
                limit=limit,
                result_count=len(formatted_results),
            )
            return formatted_results

        except Exception as e:
            # Handle and convert errors for MCP
            mcp_error = handle_mcp_tool_error(
                e,
                tool_name,
                {"query": query, "limit": limit, "provider": provider_name},
            )

            # Convert to appropriate MCP exceptions
            if isinstance(e, DataValidationError):
                raise ValueError(f"{e.message}: {e.details or ''}") from e
            else:
                raise RuntimeError(f"{display_name} search failed: {e}") from e


def create_details_tool(
    mcp: FastMCP, provider: AnimeDataProvider, tool_name: str
) -> None:
    """Create and register a details tool for a specific provider.

    Args:
        mcp: FastMCP server instance
        provider: The anime data provider
        tool_name: Name for the tool
    """
    provider_name = provider.info.name
    display_name = provider.info.display_name

    @mcp.tool(name=tool_name)
    async def provider_details_tool(anime_id: str) -> dict[str, Any]:
        f"""Get detailed information about a specific anime from {display_name}.

        Retrieve comprehensive anime data from {display_name} including synopsis, ratings,
        episode count, air dates, creators, and related anime information.

        Args:
            anime_id: Unique anime identifier for {display_name}

        Returns:
            Dictionary containing detailed anime information

        Raises:
            ValueError: If anime ID is invalid
            RuntimeError: If the API request fails or anime is not found
        """
        set_request_context(operation=f"{tool_name}_tool")
        logger.info(
            f"{display_name} details tool requested",
            provider=provider_name,
            anime_id=anime_id,
        )

        try:
            # Validate anime ID parameter
            if not anime_id or not str(anime_id).strip():
                raise DataValidationError(
                    "Anime ID cannot be empty",
                    field_name="anime_id",
                    field_value=anime_id,
                )

            # Get anime details using the provider
            details = await provider.get_anime_details(anime_id)

            # Format details for MCP response
            formatted_details = _format_anime_details_with_provider(
                details, provider_name
            )

            logger.info(
                f"{display_name} details tool completed",
                provider=provider_name,
                anime_id=anime_id,
                title=details.title,
            )
            return formatted_details

        except Exception as e:
            # Handle and convert errors for MCP
            mcp_error = handle_mcp_tool_error(
                e, tool_name, {"anime_id": anime_id, "provider": provider_name}
            )

            # Convert to appropriate MCP exceptions
            if isinstance(e, DataValidationError):
                raise ValueError(f"{e.message}: {e.details or ''}") from e
            elif isinstance(e, ProviderError) and "not found" in str(e).lower():
                raise RuntimeError(f"Anime not found in {display_name}: {e}") from e
            else:
                raise RuntimeError(f"{display_name} details fetch failed: {e}") from e


def create_recommendations_tool(
    mcp: FastMCP, provider: AnimeDataProvider, tool_name: str
) -> None:
    """Create and register a recommendations tool for a specific provider.

    Args:
        mcp: FastMCP server instance
        provider: The anime data provider
        tool_name: Name for the tool
    """
    provider_name = provider.info.name
    display_name = provider.info.display_name

    @mcp.tool(name=tool_name)
    async def provider_recommendations_tool(
        anime_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        f"""Get anime recommendations based on a specific anime from {display_name}.

        Args:
            anime_id: Unique anime identifier for {display_name}
            limit: Maximum number of recommendations to return (default: 10)

        Returns:
            List of recommended anime

        Raises:
            ValueError: If anime ID is invalid
            RuntimeError: If the API request fails
        """
        set_request_context(operation=f"{tool_name}_tool")
        logger.info(
            f"{display_name} recommendations tool requested",
            provider=provider_name,
            anime_id=anime_id,
            limit=limit,
        )

        try:
            # Validate parameters
            if not anime_id or not str(anime_id).strip():
                raise DataValidationError(
                    "Anime ID cannot be empty",
                    field_name="anime_id",
                    field_value=anime_id,
                )

            if limit < 1:
                raise DataValidationError(
                    "Limit must be at least 1",
                    field_name="limit",
                    field_value=limit,
                )

            # Get recommendations using the provider
            recommendations = await provider.get_recommendations(anime_id, limit)

            # Format results for MCP response
            formatted_results = []
            for result in recommendations:
                formatted_result = {
                    "aid": result.aid,
                    "title": result.title,
                    "type": result.type,
                    "year": result.year,
                    "provider": provider_name,
                }
                formatted_results.append(formatted_result)

            logger.info(
                f"{display_name} recommendations tool completed",
                provider=provider_name,
                anime_id=anime_id,
                result_count=len(formatted_results),
            )
            return formatted_results

        except Exception as e:
            # Handle and convert errors for MCP
            mcp_error = handle_mcp_tool_error(
                e,
                tool_name,
                {"anime_id": anime_id, "limit": limit, "provider": provider_name},
            )

            # Convert to appropriate MCP exceptions
            if isinstance(e, DataValidationError):
                raise ValueError(f"{e.message}: {e.details or ''}") from e
            else:
                raise RuntimeError(f"{display_name} recommendations failed: {e}") from e


def register_provider_tools(mcp: FastMCP, provider: AnimeDataProvider) -> list[str]:
    """Register all supported tools for a specific provider.

    Args:
        mcp: FastMCP server instance
        provider: The anime data provider

    Returns:
        List of registered tool names
    """
    provider_name = provider.info.name
    capabilities = provider.info.capabilities
    registered_tools = []

    logger.info(
        "Registering tools for provider",
        provider=provider_name,
        capabilities=capabilities.model_dump(),
    )

    # Register search tool if supported
    if capabilities.supports_search:
        tool_name = ToolNamingConvention.search_tool_name(provider_name)
        create_search_tool(mcp, provider, tool_name)
        registered_tools.append(tool_name)
        logger.debug(f"Registered search tool: {tool_name}")

    # Register details tool if supported
    if capabilities.supports_details:
        tool_name = ToolNamingConvention.details_tool_name(provider_name)
        create_details_tool(mcp, provider, tool_name)
        registered_tools.append(tool_name)
        logger.debug(f"Registered details tool: {tool_name}")

    # Register recommendations tool if supported
    if capabilities.supports_recommendations:
        tool_name = ToolNamingConvention.recommendations_tool_name(provider_name)
        create_recommendations_tool(mcp, provider, tool_name)
        registered_tools.append(tool_name)
        logger.debug(f"Registered recommendations tool: {tool_name}")

    # Additional tools can be added here for seasonal, trending, etc.

    logger.info(
        "Provider tools registered successfully",
        provider=provider_name,
        registered_tools=registered_tools,
    )

    return registered_tools


def register_all_provider_tools(
    mcp: FastMCP, registry: ProviderRegistry
) -> dict[str, list[str]]:
    """Register tools for all enabled providers in the registry.

    Args:
        mcp: FastMCP server instance
        registry: Provider registry containing enabled providers

    Returns:
        Dictionary mapping provider names to their registered tool names
    """
    logger.info("Registering tools for all enabled providers")

    all_registered_tools = {}
    enabled_providers = registry.get_enabled_providers()

    for provider_name, provider in enabled_providers.items():
        try:
            if not provider.is_initialized:
                logger.warning(
                    f"Skipping tool registration for uninitialized provider: {provider_name}"
                )
                continue

            registered_tools = register_provider_tools(mcp, provider)
            all_registered_tools[provider_name] = registered_tools

        except Exception as e:
            logger.error(
                f"Failed to register tools for provider {provider_name}",
                error=str(e),
                error_type=type(e).__name__,
            )

    total_tools = sum(len(tools) for tools in all_registered_tools.values())
    logger.info(
        "Provider tool registration completed",
        total_providers=len(all_registered_tools),
        total_tools=total_tools,
        registered_tools=all_registered_tools,
    )

    return all_registered_tools


def _format_anime_details_with_provider(
    details: AnimeDetails, provider_name: str
) -> dict[str, Any]:
    """Format AnimeDetails for MCP response with provider information.

    Args:
        details: AnimeDetails object to format
        provider_name: Name of the provider that supplied the data

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
        "provider": provider_name,
    }
