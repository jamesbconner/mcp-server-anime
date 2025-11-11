"""XML response parser for AniDB API data.

This module provides functions for parsing XML responses from the AniDB HTTP API
and transforming them into structured Pydantic models. It handles both anime search
results and detailed anime information with comprehensive error handling.
"""

import contextlib
from datetime import datetime

from lxml import etree
from pydantic import ValidationError

from mcp_server_anime.core.exceptions import XMLParsingError
from mcp_server_anime.core.logging_config import get_logger
from mcp_server_anime.core.models import (
    AnimeCharacter,
    AnimeCreator,
    AnimeDetails,
    AnimeEpisode,
    AnimeRatings,
    AnimeRecommendation,
    AnimeResources,
    AnimeSearchResult,
    AnimeTag,
    AnimeTitle,
    ExternalResource,
    RelatedAnime,
    SimilarAnime,
    VoiceActor,
)

logger = get_logger(__name__)


def _safe_get_text(element: etree._Element | None, default: str = "") -> str:
    """Safely extract text content from an XML element.

    Args:
        element: XML element to extract text from
        default: Default value if element is None or has no text

    Returns:
        Text content of the element or default value
    """
    if element is None:
        return default
    text = element.text
    return text.strip() if text else default


def _safe_get_int(element: etree._Element | None, default: int = 0) -> int:
    """Safely extract integer value from an XML element.

    Args:
        element: XML element to extract integer from
        default: Default value if element is None or conversion fails

    Returns:
        Integer value of the element or default value
    """
    if element is None:
        return default

    text = element.text
    if not text:
        return default

    try:
        return int(text.strip())
    except (ValueError, TypeError):
        logger.warning(
            f"Failed to convert '{text}' to integer, using default {default}"
        )
        return default


def _safe_get_date(element: etree._Element | None) -> datetime | None:
    """Safely extract date value from an XML element.

    Args:
        element: XML element containing date string

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if element is None:
        return None

    text = element.text
    if not text:
        return None

    text = text.strip()
    if not text:
        return None

    # Try different date formats commonly used by AniDB
    date_formats = [
        "%Y-%m-%d",  # 2023-12-25
        "%Y.%m.%d",  # 2023.12.25
        "%Y/%m/%d",  # 2023/12/25
        "%d.%m.%Y",  # 25.12.2023
        "%d/%m/%Y",  # 25/12/2023
        "%Y",  # 2023 (year only)
    ]

    for date_format in date_formats:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue

    logger.warning(f"Failed to parse date '{text}' with any known format")
    return None


def parse_anime_search_results(xml_content: str) -> list[AnimeSearchResult]:
    """Parse XML response containing anime search results.

    Args:
        xml_content: Raw XML content from AniDB search API

    Returns:
        List of AnimeSearchResult objects

    Raises:
        XMLParsingError: If XML parsing fails or data is malformed

    Example:
        >>> xml = '''<?xml version="1.0" encoding="UTF-8"?>
        ... <anime>
        ...   <anime aid="1" type="TV Series" year="1995">
        ...     <title>Neon Genesis Evangelion</title>
        ...   </anime>
        ... </anime>'''
        >>> results = parse_anime_search_results(xml)
        >>> print(results[0].title)
        'Neon Genesis Evangelion'
    """
    if not xml_content or not xml_content.strip():
        raise XMLParsingError("Empty XML content provided")

    try:
        # Parse XML with lxml
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise XMLParsingError(
            "Invalid XML syntax", xml_content=f"XML parsing failed: {e}"
        ) from e
    except Exception as e:
        raise XMLParsingError(
            "Unexpected error during XML parsing", xml_content=str(e)
        ) from e

    results: list[AnimeSearchResult] = []

    # Handle different possible root element names
    anime_elements = root.xpath(".//anime")
    if not anime_elements:
        # Try alternative xpath patterns
        anime_elements = root.xpath(".//item") or root.xpath(".//*[@aid]")

    for anime_elem in anime_elements:
        try:
            # Extract anime ID from aid attribute
            aid_str = anime_elem.get("aid")
            if not aid_str:
                logger.warning("Anime element missing 'aid' attribute, skipping")
                continue

            try:
                aid = int(aid_str)
            except (ValueError, TypeError):
                logger.warning(f"Invalid aid value '{aid_str}', skipping anime")
                continue

            # Extract title - try multiple possible element names
            title_elem = anime_elem.find("title")
            if title_elem is None:
                title_elem = anime_elem.find("name")
            if title_elem is None:
                title_elem = anime_elem.find("maintitle")

            title = _safe_get_text(title_elem)
            if not title:
                logger.warning(f"Anime {aid} missing title, skipping")
                continue

            # Extract type from attribute or element
            anime_type = anime_elem.get("type")
            if not anime_type:
                type_elem = anime_elem.find("type")
                anime_type = _safe_get_text(type_elem)

            if not anime_type:
                anime_type = "Unknown"

            # Extract year from attribute or element
            year_str = anime_elem.get("year")
            year: int | None = None
            if year_str:
                with contextlib.suppress(ValueError, TypeError):
                    year = int(year_str)
            else:
                year_elem = anime_elem.find("year")
                year = _safe_get_int(year_elem) if year_elem is not None else None
                if year == 0:
                    year = None

            # Create and validate the search result
            try:
                result = AnimeSearchResult(
                    aid=aid, title=title, type=anime_type, year=year
                )
                results.append(result)
            except ValidationError as e:
                logger.warning(f"Validation failed for anime {aid}: {e}")
                continue

        except Exception as e:
            logger.warning(f"Error processing anime element: {e}")
            continue

    logger.info(f"Successfully parsed {len(results)} anime search results")
    return results


def parse_anime_details(xml_content: str) -> AnimeDetails:
    """Parse XML response containing detailed anime information.

    Args:
        xml_content: Raw XML content from AniDB anime details API

    Returns:
        AnimeDetails object with comprehensive anime information

    Raises:
        XMLParsingError: If XML parsing fails or required data is missing

    Example:
        >>> xml = '''<?xml version="1.0" encoding="UTF-8"?>
        ... <anime aid="1" restricted="false">
        ...   <type>TV Series</type>
        ...   <episodecount>26</episodecount>
        ...   <title>Neon Genesis Evangelion</title>
        ...   <startdate>1995-10-04</startdate>
        ...   <enddate>1996-03-27</enddate>
        ... </anime>'''
        >>> details = parse_anime_details(xml)
        >>> print(details.episode_count)
        26
    """
    if not xml_content or not xml_content.strip():
        raise XMLParsingError("Empty XML content provided")

    try:
        # Parse XML with lxml
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise XMLParsingError(
            "Invalid XML syntax", xml_content=f"XML parsing failed: {e}"
        ) from e
    except Exception as e:
        raise XMLParsingError(
            "Unexpected error during XML parsing", xml_content=str(e)
        ) from e

    # Find the main anime element
    anime_elem = root if root.tag == "anime" else root.find(".//anime")
    if anime_elem is None:
        raise XMLParsingError("No anime element found in XML")

    # Extract required fields
    aid_str = anime_elem.get("aid") or anime_elem.get(
        "id"
    )  # AniDB uses 'id' attribute in HTTP API
    if not aid_str:
        raise XMLParsingError("Anime element missing required 'aid' or 'id' attribute")

    try:
        aid = int(aid_str)
    except (ValueError, TypeError) as e:
        raise XMLParsingError(f"Invalid aid value '{aid_str}'") from e

    # Extract main title from titles container
    titles_elem = anime_elem.find("titles")
    title = None

    if titles_elem is not None:
        # Look for main title first
        main_title_elem = titles_elem.find(".//title[@type='main']")
        if main_title_elem is not None:
            title = _safe_get_text(main_title_elem)
        else:
            # Fallback to first title
            first_title_elem = titles_elem.find("title")
            if first_title_elem is not None:
                title = _safe_get_text(first_title_elem)

    # Fallback to direct title element (for compatibility)
    if not title:
        title_elem = anime_elem.find("title")
        if title_elem is None:
            title_elem = anime_elem.find("maintitle")
        if title_elem is None:
            title_elem = anime_elem.find("name")
        title = _safe_get_text(title_elem)

    if not title:
        raise XMLParsingError("Anime missing required title")

    # Extract type
    type_elem = anime_elem.find("type")
    anime_type = _safe_get_text(type_elem, "Unknown")

    # Extract episode count
    episode_elem = anime_elem.find("episodecount")
    episode_count = _safe_get_int(episode_elem, 0)

    # Extract dates
    start_date = _safe_get_date(anime_elem.find("startdate"))
    end_date = _safe_get_date(anime_elem.find("enddate"))

    # Extract synopsis/description
    synopsis_elem = anime_elem.find("description")
    if synopsis_elem is None:
        synopsis_elem = anime_elem.find("synopsis")
    if synopsis_elem is None:
        synopsis_elem = anime_elem.find("summary")

    synopsis = _safe_get_text(synopsis_elem) if synopsis_elem is not None else None
    if synopsis == "":
        synopsis = None

    # Extract URL
    url_elem = anime_elem.find("url")
    url = _safe_get_text(url_elem) if url_elem is not None else None
    if url == "":
        url = None

    # Extract restricted flag
    restricted_str = anime_elem.get("restricted", "false")
    restricted = restricted_str.lower() in ("true", "1", "yes")

    # Parse titles
    titles = _parse_titles(anime_elem)

    # Parse creators
    creators = _parse_creators(anime_elem)

    # Parse related anime
    related_anime = _parse_related_anime(anime_elem)

    # Parse ratings
    ratings = _parse_ratings(anime_elem)

    # Parse similar anime
    similar_anime = _parse_similar_anime(anime_elem)

    # Extract picture
    picture_elem = anime_elem.find("picture")
    picture = _safe_get_text(picture_elem) if picture_elem is not None else None
    if picture == "":
        picture = None

    # Parse enhanced data sections with error handling
    episodes: list[AnimeEpisode] = []
    resources: AnimeResources | None = None
    characters: list[AnimeCharacter] = []
    tags: list[AnimeTag] = []
    recommendations: list[AnimeRecommendation] = []

    try:
        episodes = _parse_episodes(anime_elem)
        logger.debug(f"Parsed {len(episodes)} episodes for anime {aid}")
    except Exception as e:
        logger.warning(f"Failed to parse episodes for anime {aid}: {e}")

    try:
        resources = _parse_resources(anime_elem)
        if resources:
            total_resources = (
                len(resources.myanimelist)
                + len(resources.imdb)
                + len(resources.official_sites)
                + len(resources.other)
            )
            logger.debug(f"Parsed {total_resources} resources for anime {aid}")
    except Exception as e:
        logger.warning(f"Failed to parse resources for anime {aid}: {e}")

    try:
        characters = _parse_characters(anime_elem)
        logger.debug(f"Parsed {len(characters)} characters for anime {aid}")
    except Exception as e:
        logger.warning(f"Failed to parse characters for anime {aid}: {e}")

    try:
        tags = _parse_tags(anime_elem)
        logger.debug(f"Parsed {len(tags)} tags for anime {aid}")
    except Exception as e:
        logger.warning(f"Failed to parse tags for anime {aid}: {e}")

    try:
        recommendations = _parse_recommendations(anime_elem)
        logger.debug(f"Parsed {len(recommendations)} recommendations for anime {aid}")
    except Exception as e:
        logger.warning(f"Failed to parse recommendations for anime {aid}: {e}")

    try:
        return AnimeDetails(
            aid=aid,
            title=title,
            type=anime_type,
            episode_count=episode_count,
            start_date=start_date,
            end_date=end_date,
            titles=titles,
            synopsis=synopsis,
            url=url,
            creators=creators,
            related_anime=related_anime,
            restricted=restricted,
            ratings=ratings,
            similar_anime=similar_anime,
            picture=picture,
            # Enhanced fields
            episodes=episodes,
            resources=resources,
            characters=characters,
            tags=tags,
            recommendations=recommendations,
        )
    except ValidationError as e:
        raise XMLParsingError(
            "Failed to create AnimeDetails object", xml_content=f"Validation error: {e}"
        ) from e


def _parse_titles(anime_elem: etree._Element) -> list[AnimeTitle]:
    """Parse title elements from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of AnimeTitle objects
    """
    titles: list[AnimeTitle] = []

    # Look for titles container or individual title elements
    titles_container = anime_elem.find("titles")
    if titles_container is not None:
        title_elements = titles_container.findall("title")
    else:
        # Look for title elements directly under anime
        title_elements = anime_elem.findall("title[@type]")

    for title_elem in title_elements:
        try:
            title_text = _safe_get_text(title_elem)
            if not title_text:
                continue

            # Extract attributes
            title_type = title_elem.get("type", "unknown")
            # Try both xml:lang and lang attributes
            language = title_elem.get(
                "{http://www.w3.org/XML/1998/namespace}lang"
            ) or title_elem.get("lang", "unknown")

            # Normalize title type
            if title_type.lower() in ("main", "primary"):
                title_type = "main"
            elif title_type.lower() in ("official", "formal"):
                title_type = "official"
            elif title_type.lower() in ("synonym", "alternative", "alt"):
                title_type = "synonym"
            elif title_type.lower() in ("short", "abbreviated"):
                title_type = "short"

            title_obj = AnimeTitle(title=title_text, language=language, type=title_type)
            titles.append(title_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse title element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing title: {e}")
            continue

    return titles


def _parse_creators(anime_elem: etree._Element) -> list[AnimeCreator]:
    """Parse creator/staff elements from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of AnimeCreator objects
    """
    creators: list[AnimeCreator] = []

    # Look for creators/staff container or individual creator elements
    creators_container = anime_elem.find("creators")
    if creators_container is None:
        creators_container = anime_elem.find("staff")
    if creators_container is None:
        creators_container = anime_elem.find("people")

    if creators_container is not None:
        # Look for name elements within creators container (AniDB format)
        creator_elements = creators_container.findall("name")
        if not creator_elements:
            creator_elements = creators_container.findall("creator")
        if not creator_elements:
            creator_elements = creators_container.findall("staff")
        if not creator_elements:
            creator_elements = creators_container.findall("person")
    else:
        # Look for creator elements directly under anime
        creator_elements = anime_elem.findall("creator")
        if not creator_elements:
            creator_elements = anime_elem.findall("staff")
        if not creator_elements:
            creator_elements = anime_elem.findall("person")

    for creator_elem in creator_elements:
        try:
            # For AniDB format, the name is the text content of the element
            if creator_elem.tag == "name":
                name = _safe_get_text(creator_elem)
            else:
                name_elem = creator_elem.find("name")
                if name_elem is not None:
                    name = _safe_get_text(name_elem)
                else:
                    name = _safe_get_text(creator_elem)

            if not name:
                continue

            # Extract creator ID
            creator_id_str = creator_elem.get("id")
            if not creator_id_str:
                id_elem = creator_elem.find("id")
                if id_elem is not None:
                    creator_id_str = _safe_get_text(id_elem)

            if not creator_id_str:
                continue

            try:
                creator_id = int(creator_id_str)
            except (ValueError, TypeError):
                continue

            # Extract role/type
            role = creator_elem.get("type")
            if not role:
                role = creator_elem.get("role")
            if not role:
                role_elem = creator_elem.find("type")
                if role_elem is None:
                    role_elem = creator_elem.find("role")
                role = _safe_get_text(role_elem, "Unknown")

            creator_obj = AnimeCreator(name=name, id=creator_id, type=role)
            creators.append(creator_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse creator element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing creator: {e}")
            continue

    return creators


def _parse_related_anime(anime_elem: etree._Element) -> list[RelatedAnime]:
    """Parse related anime elements from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of RelatedAnime objects
    """
    related: list[RelatedAnime] = []

    # Look for related anime container or individual related elements
    related_container = anime_elem.find("relatedanime")
    if related_container is None:
        related_container = anime_elem.find("related")
    if related_container is None:
        related_container = anime_elem.find("relations")

    if related_container is not None:
        related_elements = related_container.findall("anime")
        if not related_elements:
            related_elements = related_container.findall("relation")
        if not related_elements:
            related_elements = related_container.findall("related")
    else:
        # Look for related elements directly under anime
        related_elements = anime_elem.findall("related[@aid]")

    for related_elem in related_elements:
        try:
            # Extract related anime ID (try both id and aid attributes)
            aid_str = related_elem.get("id") or related_elem.get("aid")
            if not aid_str:
                aid_elem = related_elem.find("aid")
                if aid_elem is None:
                    aid_elem = related_elem.find("id")
                if aid_elem is not None:
                    aid_str = _safe_get_text(aid_elem)

            if not aid_str:
                continue

            try:
                aid = int(aid_str)
            except (ValueError, TypeError):
                continue

            # Extract title
            title_elem = related_elem.find("title")
            if title_elem is not None:
                title = _safe_get_text(title_elem)
            else:
                title = _safe_get_text(related_elem)

            if not title:
                continue

            # Extract relation type
            relation_type = related_elem.get("type")
            if not relation_type:
                relation_type = related_elem.get("relation")
            if not relation_type:
                type_elem = related_elem.find("type")
                if type_elem is None:
                    type_elem = related_elem.find("relation")
                relation_type = _safe_get_text(type_elem, "Related")

            related_obj = RelatedAnime(aid=aid, title=title, type=relation_type)
            related.append(related_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse related anime element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing related anime: {e}")
            continue

    return related


def _parse_ratings(anime_elem: etree._Element) -> AnimeRatings | None:
    """Parse ratings elements from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        AnimeRatings object or None if no ratings found
    """
    ratings_container = anime_elem.find("ratings")
    if ratings_container is None:
        return None

    try:
        # Extract permanent rating
        permanent_elem = ratings_container.find("permanent")
        permanent = None
        permanent_count = None
        if permanent_elem is not None:
            permanent_text = _safe_get_text(permanent_elem)
            if permanent_text:
                with contextlib.suppress(ValueError, TypeError):
                    permanent = float(permanent_text)
            permanent_count_str = permanent_elem.get("count")
            if permanent_count_str:
                with contextlib.suppress(ValueError, TypeError):
                    permanent_count = int(permanent_count_str)

        # Extract temporary rating
        temporary_elem = ratings_container.find("temporary")
        temporary = None
        temporary_count = None
        if temporary_elem is not None:
            temporary_text = _safe_get_text(temporary_elem)
            if temporary_text:
                with contextlib.suppress(ValueError, TypeError):
                    temporary = float(temporary_text)
            temporary_count_str = temporary_elem.get("count")
            if temporary_count_str:
                with contextlib.suppress(ValueError, TypeError):
                    temporary_count = int(temporary_count_str)

        # Extract review rating
        review_elem = ratings_container.find("review")
        review = None
        review_count = None
        if review_elem is not None:
            review_text = _safe_get_text(review_elem)
            if review_text:
                with contextlib.suppress(ValueError, TypeError):
                    review = float(review_text)
            review_count_str = review_elem.get("count")
            if review_count_str:
                with contextlib.suppress(ValueError, TypeError):
                    review_count = int(review_count_str)

        # Only return ratings if at least one rating is found
        if permanent is not None or temporary is not None or review is not None:
            return AnimeRatings(
                permanent=permanent,
                temporary=temporary,
                review=review,
                permanent_count=permanent_count,
                temporary_count=temporary_count,
                review_count=review_count,
            )

    except Exception as e:
        logger.warning(f"Failed to parse ratings: {e}")

    return None


def _parse_similar_anime(anime_elem: etree._Element) -> list[SimilarAnime]:
    """Parse similar anime elements from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of SimilarAnime objects
    """
    similar: list[SimilarAnime] = []

    similar_container = anime_elem.find("similaranime")
    if similar_container is None:
        return similar

    anime_elements = similar_container.findall("anime")

    for anime_elem in anime_elements:
        try:
            # Extract anime ID
            aid_str = anime_elem.get("id") or anime_elem.get("aid")
            if not aid_str:
                continue

            try:
                aid = int(aid_str)
            except (ValueError, TypeError):
                continue

            # Extract title
            title = _safe_get_text(anime_elem)
            if not title:
                continue

            # Extract approval and total counts
            approval_str = anime_elem.get("approval")
            approval = None
            if approval_str:
                with contextlib.suppress(ValueError, TypeError):
                    approval = int(approval_str)

            total_str = anime_elem.get("total")
            total = None
            if total_str:
                with contextlib.suppress(ValueError, TypeError):
                    total = int(total_str)

            similar_obj = SimilarAnime(
                aid=aid,
                title=title,
                approval=approval,
                total=total,
            )
            similar.append(similar_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse similar anime element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing similar anime: {e}")
            continue

    return similar


def _parse_episodes(anime_elem: etree._Element) -> list[AnimeEpisode]:
    """Parse episode elements from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of AnimeEpisode objects
    """
    episodes: list[AnimeEpisode] = []

    # Look for episodes container
    episodes_container = anime_elem.find("episodes")
    if episodes_container is None:
        return episodes

    episode_elements = episodes_container.findall("episode")

    for episode_elem in episode_elements:
        try:
            # Extract episode number (required)
            episode_num_str = episode_elem.get("id")
            if not episode_num_str:
                # Try alternative attribute names
                episode_num_str = episode_elem.get("number")
            if not episode_num_str:
                # Try element content
                num_elem = episode_elem.find("epno")
                if num_elem is not None:
                    episode_num_str = _safe_get_text(num_elem)

            if not episode_num_str:
                continue

            try:
                episode_number = int(episode_num_str)
            except (ValueError, TypeError):
                continue

            if episode_number <= 0:
                continue

            # Extract episode title
            title_elem = episode_elem.find("title")
            if title_elem is None:
                title_elem = episode_elem.find("name")
            title = _safe_get_text(title_elem) if title_elem is not None else None
            if title == "":
                title = None

            # Extract air date
            air_date = None
            air_date_elem = episode_elem.find("airdate")
            if air_date_elem is not None:
                air_date = _safe_get_date(air_date_elem)

            # Extract description/summary
            desc_elem = episode_elem.find("summary")
            if desc_elem is None:
                desc_elem = episode_elem.find("description")
            description = _safe_get_text(desc_elem) if desc_elem is not None else None
            if description == "":
                description = None

            # Extract episode length
            length = None
            length_elem = episode_elem.find("length")
            if length_elem is not None:
                length_str = _safe_get_text(length_elem)
                if length_str:
                    try:
                        length = int(length_str)
                        if length <= 0:
                            length = None
                    except (ValueError, TypeError):
                        pass

            episode_obj = AnimeEpisode(
                episode_number=episode_number,
                title=title,
                air_date=air_date,
                description=description,
                length=length,
            )
            episodes.append(episode_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse episode element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing episode: {e}")
            continue

    # Sort episodes by episode number
    episodes.sort(key=lambda ep: ep.episode_number)
    return episodes


def _parse_resources(anime_elem: etree._Element) -> AnimeResources | None:
    """Parse external resource links from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        AnimeResources object or None if no resources found
    """
    # Look for resources container
    resources_container = anime_elem.find("resources")
    if resources_container is None:
        return None

    myanimelist_resources: list[ExternalResource] = []
    imdb_resources: list[ExternalResource] = []
    official_sites: list[ExternalResource] = []
    other_resources: list[ExternalResource] = []

    resource_elements = resources_container.findall("resource")

    for resource_elem in resource_elements:
        try:
            # Extract resource type
            resource_type_str = resource_elem.get("type")
            if not resource_type_str:
                continue

            try:
                resource_type_id = int(resource_type_str)
            except (ValueError, TypeError):
                continue

            # Extract external identifier
            identifier = resource_elem.get("externalentity")
            if not identifier:
                identifier = _safe_get_text(resource_elem)
            if identifier == "":
                identifier = None

            # Extract URL if available
            url = resource_elem.get("url")
            if url == "":
                url = None

            # Map resource type to platform and create resource object
            platform_name = _map_resource_type_to_platform(resource_type_id)

            resource_obj = ExternalResource(
                type=platform_name,
                identifier=identifier,
                url=url,
            )

            # Categorize by platform
            if resource_type_id == 1:  # MyAnimeList
                myanimelist_resources.append(resource_obj)
            elif resource_type_id == 43:  # IMDB
                imdb_resources.append(resource_obj)
            elif resource_type_id in [4, 6, 7]:  # Official sites, Wikipedia
                official_sites.append(resource_obj)
            else:
                other_resources.append(resource_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse resource element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing resource: {e}")
            continue

    # Only return resources if at least one was found
    if myanimelist_resources or imdb_resources or official_sites or other_resources:
        return AnimeResources(
            myanimelist=myanimelist_resources,
            imdb=imdb_resources,
            official_sites=official_sites,
            other=other_resources,
        )

    return None


def _map_resource_type_to_platform(resource_type_id: int) -> str:
    """Map AniDB resource type ID to platform name.

    Args:
        resource_type_id: AniDB resource type identifier

    Returns:
        Platform name string
    """
    resource_type_mapping = {
        1: "MyAnimeList",
        2: "AnimeNfo",
        3: "AnimeNewsNetwork",
        4: "Official Homepage",
        6: "Wikipedia (EN)",
        7: "Wikipedia (JP)",
        43: "IMDB",
        44: "The Movie Database",
    }

    return resource_type_mapping.get(resource_type_id, f"Unknown ({resource_type_id})")


def _parse_characters(anime_elem: etree._Element) -> list[AnimeCharacter]:
    """Parse character information from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of AnimeCharacter objects
    """
    characters: list[AnimeCharacter] = []

    # Look for characters container
    characters_container = anime_elem.find("characters")
    if characters_container is None:
        return characters

    character_elements = characters_container.findall("character")

    for char_elem in character_elements:
        try:
            # Extract character ID
            char_id_str = char_elem.get("id")
            char_id = None
            if char_id_str:
                with contextlib.suppress(ValueError, TypeError):
                    char_id = int(char_id_str)

            # Extract character name (required)
            name_elem = char_elem.find("name")
            if name_elem is None:
                name_elem = char_elem.find("charactername")
            name = _safe_get_text(name_elem) if name_elem is not None else None

            if not name:
                continue

            # Extract character description
            desc_elem = char_elem.find("description")
            if desc_elem is None:
                desc_elem = char_elem.find("characterdescription")
            description = _safe_get_text(desc_elem) if desc_elem is not None else None
            if description == "":
                description = None

            # Extract character type
            type_elem = char_elem.find("charactertype")
            if type_elem is None:
                type_elem = char_elem.find("type")
            character_type = (
                _safe_get_text(type_elem) if type_elem is not None else None
            )
            if character_type == "":
                character_type = None

            # Parse voice actors
            voice_actors = _parse_voice_actors(char_elem)

            character_obj = AnimeCharacter(
                name=name,
                id=char_id,
                description=description,
                voice_actors=voice_actors,
                character_type=character_type,
            )
            characters.append(character_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse character element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing character: {e}")
            continue

    return characters


def _parse_voice_actors(char_elem: etree._Element) -> list[VoiceActor]:
    """Parse voice actor information from character XML element.

    Args:
        char_elem: The character XML element

    Returns:
        List of VoiceActor objects
    """
    voice_actors: list[VoiceActor] = []

    # Look for seiyuu/voice actor container
    seiyuu_container = char_elem.find("seiyuu")
    if seiyuu_container is None:
        seiyuu_container = char_elem.find("voiceactors")
    if seiyuu_container is None:
        return voice_actors

    seiyuu_elements = seiyuu_container.findall("seiyuu")
    if not seiyuu_elements:
        seiyuu_elements = seiyuu_container.findall("voiceactor")

    for seiyuu_elem in seiyuu_elements:
        try:
            # Extract voice actor ID
            va_id_str = seiyuu_elem.get("id")
            va_id = None
            if va_id_str:
                with contextlib.suppress(ValueError, TypeError):
                    va_id = int(va_id_str)

            # Extract voice actor name (required)
            name = _safe_get_text(seiyuu_elem)
            if not name:
                name_elem = seiyuu_elem.find("name")
                name = _safe_get_text(name_elem) if name_elem is not None else None

            if not name:
                continue

            # Extract language
            language = seiyuu_elem.get("lang")
            if not language:
                language = seiyuu_elem.get("language")
            if language == "":
                language = None

            voice_actor_obj = VoiceActor(
                name=name,
                id=va_id,
                language=language,
            )
            voice_actors.append(voice_actor_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse voice actor element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing voice actor: {e}")
            continue

    return voice_actors


def _parse_tags(anime_elem: etree._Element) -> list[AnimeTag]:
    """Parse tag and genre information from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of AnimeTag objects
    """
    tags: list[AnimeTag] = []

    # Look for tags container
    tags_container = anime_elem.find("tags")
    if tags_container is None:
        return tags

    tag_elements = tags_container.findall("tag")

    for tag_elem in tag_elements:
        try:
            # Extract tag ID (required)
            tag_id_str = tag_elem.get("id")
            if not tag_id_str:
                continue

            try:
                tag_id = int(tag_id_str)
            except (ValueError, TypeError):
                continue

            # Extract tag name (required)
            name_elem = tag_elem.find("name")
            name = _safe_get_text(name_elem) if name_elem is not None else None

            if not name:
                continue

            # Extract tag description
            desc_elem = tag_elem.find("description")
            description = _safe_get_text(desc_elem) if desc_elem is not None else None
            if description == "":
                description = None

            # Extract tag weight
            weight_str = tag_elem.get("weight")
            weight = None
            if weight_str:
                try:
                    weight = int(weight_str)
                    if weight < 0 or weight > 600:
                        weight = None
                except (ValueError, TypeError):
                    pass

            # Extract spoiler flag
            spoiler_str = tag_elem.get("spoiler")
            spoiler = spoiler_str is not None and spoiler_str.lower() in (
                "true",
                "1",
                "yes",
            )

            # Extract verified flag
            verified_str = tag_elem.get("verified")
            verified = verified_str is not None and verified_str.lower() in (
                "true",
                "1",
                "yes",
            )

            # Extract parent tag ID
            parent_id_str = tag_elem.get("parentid")
            parent_id = None
            if parent_id_str:
                with contextlib.suppress(ValueError, TypeError):
                    parent_id = int(parent_id_str)

            tag_obj = AnimeTag(
                id=tag_id,
                name=name,
                description=description,
                weight=weight,
                spoiler=spoiler,
                verified=verified,
                parent_id=parent_id,
            )
            tags.append(tag_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse tag element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing tag: {e}")
            continue

    # Sort tags by weight (highest first) if weights are available
    tags.sort(key=lambda tag: tag.weight or 0, reverse=True)
    return tags


def _parse_recommendations(anime_elem: etree._Element) -> list[AnimeRecommendation]:
    """Parse user recommendations from anime XML.

    Args:
        anime_elem: The anime XML element

    Returns:
        List of AnimeRecommendation objects
    """
    recommendations: list[AnimeRecommendation] = []

    # Look for recommendations container
    recommendations_container = anime_elem.find("recommendations")
    if recommendations_container is None:
        return recommendations

    recommendation_elements = recommendations_container.findall("recommendation")

    for rec_elem in recommendation_elements:
        try:
            # Extract recommendation type
            rec_type = rec_elem.get("type")
            if not rec_type:
                type_elem = rec_elem.find("type")
                rec_type = _safe_get_text(type_elem) if type_elem is not None else None

            if not rec_type:
                rec_type = "Recommended"  # Default type

            # Extract recommendation text (required)
            text_elem = rec_elem.find("text")
            if text_elem is None:
                text_elem = rec_elem.find("comment")
            text = _safe_get_text(text_elem) if text_elem is not None else None

            if not text:
                # Try getting text from element content
                text = _safe_get_text(rec_elem)

            if not text:
                continue

            # Basic content filtering - remove excessive whitespace and newlines
            text = " ".join(text.split())

            # Extract user ID
            user_id_str = rec_elem.get("uid")
            if not user_id_str:
                user_id_str = rec_elem.get("userid")
            user_id = None
            if user_id_str:
                with contextlib.suppress(ValueError, TypeError):
                    user_id = int(user_id_str)

            recommendation_obj = AnimeRecommendation(
                type=rec_type,
                text=text,
                user_id=user_id,
            )
            recommendations.append(recommendation_obj)

        except ValidationError as e:
            logger.warning(f"Failed to parse recommendation element: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error parsing recommendation: {e}")
            continue

    return recommendations


def validate_xml_response(xml_content: str) -> None:
    """Validate that XML content is well-formed and parseable.

    Args:
        xml_content: Raw XML content to validate

    Raises:
        XMLParsingError: If XML is malformed or empty
    """
    if not xml_content or not xml_content.strip():
        raise XMLParsingError("Empty XML content provided")

    try:
        etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise XMLParsingError(
            "Invalid XML syntax", xml_content=f"XML validation failed: {e}"
        ) from e
    except Exception as e:
        raise XMLParsingError(
            "Unexpected error during XML validation", xml_content=str(e)
        ) from e
