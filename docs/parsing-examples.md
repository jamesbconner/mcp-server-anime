# Enhanced AniDB Details Parsing - Usage Examples

This document provides comprehensive examples of how to use the enhanced AniDB details parsing functionality, which includes episodes, external resources, characters, tags, and recommendations.

## Overview

The enhanced parsing functionality extends the existing AniDB details MCP tool to provide richer data about anime. All enhanced fields are optional and maintain backward compatibility with existing code.

## Basic Usage

```python
from src.mcp_server_anime.tools import anidb_details

# Get enhanced anime details
details = await anidb_details(30)  # Neon Genesis Evangelion

print(f"Title: {details['title']}")
print(f"Episodes: {details['episode_count']}")
print(f"Type: {details['type']}")
```

## Working with Episodes

The `episodes` field contains detailed information about individual episodes:

```python
details = await anidb_details(30)

# Access episode information
episodes = details['episodes']
print(f"Available episode data: {len(episodes)} episodes")

for episode in episodes[:5]:  # Show first 5 episodes
    print(f"Episode {episode['episode_number']}: {episode['title']}")
    if episode['air_date']:
        print(f"  Aired: {episode['air_date']}")
    if episode['description']:
        print(f"  Summary: {episode['description'][:100]}...")
    if episode['length']:
        print(f"  Duration: {episode['length']} minutes")
    print()
```

### Episode Data Structure

```python
episode = {
    "episode_number": 1,
    "title": "Angel Attack",
    "air_date": "1995-10-04T00:00:00",  # ISO format datetime string
    "description": "The first Angel appears in Tokyo-3...",
    "length": 24  # Duration in minutes
}
```

## Working with External Resources

The `resources` field provides links to external databases and official sites:

```python
details = await anidb_details(30)

resources = details['resources']
if resources:
    # MyAnimeList links
    if resources['myanimelist']:
        for mal_entry in resources['myanimelist']:
            print(f"MyAnimeList: {mal_entry['url']}")
            print(f"  ID: {mal_entry['identifier']}")

    # IMDB links
    if resources['imdb']:
        for imdb_entry in resources['imdb']:
            print(f"IMDB: {imdb_entry['identifier']}")

    # Official sites
    if resources['official_sites']:
        for site in resources['official_sites']:
            print(f"Official Site: {site['url']}")

    # Other resources
    if resources['other']:
        for other in resources['other']:
            print(f"{other['type']}: {other['url'] or other['identifier']}")
```

### Resource Data Structure

```python
resources = {
    "myanimelist": [
        {
            "type": "MyAnimeList",
            "identifier": "30",
            "url": "https://myanimelist.net/anime/30"
        }
    ],
    "imdb": [
        {
            "type": "IMDB",
            "identifier": "tt0112159",
            "url": None
        }
    ],
    "official_sites": [
        {
            "type": "Official Homepage",
            "identifier": None,
            "url": "https://www.evangelion.co.jp/"
        }
    ],
    "other": []
}
```

## Working with Characters

The `characters` field contains information about anime characters and their voice actors:

```python
details = await anidb_details(30)

characters = details['characters']
print(f"Character information available for {len(characters)} characters")

for character in characters:
    print(f"Character: {character['name']}")
    if character['description']:
        print(f"  Description: {character['description'][:100]}...")
    if character['character_type']:
        print(f"  Type: {character['character_type']}")

    # Voice actors
    if character['voice_actors']:
        print("  Voice Actors:")
        for va in character['voice_actors']:
            lang_info = f" ({va['language']})" if va['language'] else ""
            print(f"    - {va['name']}{lang_info}")
    print()
```

### Character Data Structure

```python
character = {
    "name": "Shinji Ikari",
    "id": 89,
    "description": "The main protagonist, a reluctant Eva pilot...",
    "character_type": "Main",
    "voice_actors": [
        {
            "name": "Megumi Ogata",
            "id": 123,
            "language": "ja"
        },
        {
            "name": "Spike Spencer",
            "id": 456,
            "language": "en"
        }
    ]
}
```

## Working with Tags

The `tags` field provides genre and content categorization information:

```python
details = await anidb_details(30)

tags = details['tags']
print(f"Tags available: {len(tags)}")

# Tags are sorted by weight (most relevant first)
print("Most relevant tags:")
for tag in tags[:10]:  # Show top 10 tags
    weight_info = f" (weight: {tag['weight']})" if tag['weight'] else ""
    spoiler_info = " [SPOILER]" if tag['spoiler'] else ""
    verified_info = " ✓" if tag['verified'] else ""

    print(f"  {tag['name']}{weight_info}{spoiler_info}{verified_info}")
    if tag['description']:
        print(f"    {tag['description']}")
```

### Tag Data Structure

```python
tag = {
    "id": 2274,
    "name": "robot",
    "description": "Mecha/robot anime featuring giant robots.",
    "weight": 600,  # Higher weight = more relevant (0-600 scale)
    "spoiler": False,
    "verified": True,
    "parent_id": None  # For hierarchical tag relationships
}
```

### Filtering Tags

```python
# Filter by weight (high relevance only)
high_relevance_tags = [tag for tag in tags if tag['weight'] and tag['weight'] >= 400]

# Filter out spoiler tags
safe_tags = [tag for tag in tags if not tag['spoiler']]

# Filter by verification status
verified_tags = [tag for tag in tags if tag['verified']]

# Group by weight ranges
weight_groups = {
    'high': [tag for tag in tags if tag['weight'] and tag['weight'] >= 500],
    'medium': [tag for tag in tags if tag['weight'] and 300 <= tag['weight'] < 500],
    'low': [tag for tag in tags if tag['weight'] and tag['weight'] < 300]
}
```

## Working with Recommendations

The `recommendations` field contains user reviews and recommendations:

```python
details = await anidb_details(30)

recommendations = details['recommendations']
print(f"User recommendations: {len(recommendations)}")

# Group by recommendation type
rec_by_type = {}
for rec in recommendations:
    rec_type = rec['type']
    if rec_type not in rec_by_type:
        rec_by_type[rec_type] = []
    rec_by_type[rec_type].append(rec)

# Display by type
for rec_type, recs in rec_by_type.items():
    print(f"\n{rec_type} ({len(recs)} recommendations):")
    for rec in recs[:3]:  # Show first 3 of each type
        user_info = f" (User {rec['user_id']})" if rec['user_id'] else ""
        print(f"  {rec['text'][:100]}...{user_info}")
```

### Recommendation Data Structure

```python
recommendation = {
    "type": "Must See",
    "text": "A masterpiece of anime that redefined the mecha genre...",
    "user_id": 12345
}
```

## Complete Example: Comprehensive Anime Analysis

```python
async def analyze_anime(aid: int):
    """Comprehensive analysis of an anime using enhanced data."""
    details = await anidb_details(aid)

    print(f"=== {details['title']} ===")
    print(f"Type: {details['type']} | Episodes: {details['episode_count']}")

    if details['start_date']:
        print(f"Aired: {details['start_date'][:10]}", end="")
        if details['end_date']:
            print(f" to {details['end_date'][:10]}")
        else:
            print(" (ongoing)")

    if details['synopsis']:
        print(f"\nSynopsis: {details['synopsis'][:200]}...")

    # Episode analysis
    episodes = details['episodes']
    if episodes:
        print(f"\n📺 Episode Data Available: {len(episodes)} episodes")
        avg_length = sum(ep['length'] for ep in episodes if ep['length']) / len([ep for ep in episodes if ep['length']])
        if avg_length:
            print(f"Average episode length: {avg_length:.0f} minutes")

    # Character analysis
    characters = details['characters']
    if characters:
        print(f"\n👥 Characters: {len(characters)} characters")
        main_chars = [c for c in characters if c['character_type'] == 'Main']
        print(f"Main characters: {len(main_chars)}")

        # Voice actor languages
        languages = set()
        for char in characters:
            for va in char['voice_actors']:
                if va['language']:
                    languages.add(va['language'])
        if languages:
            print(f"Voice acting languages: {', '.join(sorted(languages))}")

    # Tag analysis
    tags = details['tags']
    if tags:
        print(f"\n🏷️  Tags: {len(tags)} tags")
        high_weight_tags = [tag for tag in tags if tag['weight'] and tag['weight'] >= 400]
        print(f"High relevance tags: {', '.join(tag['name'] for tag in high_weight_tags[:5])}")

        spoiler_count = sum(1 for tag in tags if tag['spoiler'])
        if spoiler_count:
            print(f"Spoiler tags: {spoiler_count}")

    # External resources
    resources = details['resources']
    if resources:
        print(f"\n🔗 External Links:")
        if resources['myanimelist']:
            print(f"  MyAnimeList: {resources['myanimelist'][0]['url']}")
        if resources['imdb']:
            print(f"  IMDB: {resources['imdb'][0]['identifier']}")
        if resources['official_sites']:
            print(f"  Official sites: {len(resources['official_sites'])}")

    # Recommendation summary
    recommendations = details['recommendations']
    if recommendations:
        print(f"\n⭐ User Recommendations: {len(recommendations)}")
        rec_types = {}
        for rec in recommendations:
            rec_types[rec['type']] = rec_types.get(rec['type'], 0) + 1
        for rec_type, count in rec_types.items():
            print(f"  {rec_type}: {count}")

# Usage
await analyze_anime(30)  # Neon Genesis Evangelion
```

## Error Handling

The enhanced parsing is designed to be resilient. If any enhanced section fails to parse, the basic anime information will still be returned:

```python
details = await anidb_details(aid)

# Always check if enhanced fields are available
if details['episodes']:
    # Process episodes
    pass
else:
    print("No episode data available")

if details['resources']:
    # Process resources
    pass
else:
    print("No external resource links available")

# Enhanced fields will be empty lists or None if not available
assert isinstance(details['episodes'], list)
assert isinstance(details['characters'], list)
assert isinstance(details['tags'], list)
assert isinstance(details['recommendations'], list)
assert details['resources'] is None or isinstance(details['resources'], dict)
```

## Backward Compatibility

All existing code will continue to work unchanged. The enhanced fields are additive:

```python
# Existing code continues to work
details = await anidb_details(30)
print(details['title'])  # Still works
print(details['episode_count'])  # Still works
print(details['creators'])  # Still works

# New fields are available but optional
print(details['episodes'])  # New field
print(details['characters'])  # New field
```

## Performance Considerations

The enhanced parsing adds minimal overhead. For optimal performance:

1. **Selective Processing**: Only process the enhanced fields you need
2. **Caching**: The enhanced data is cached along with basic data
3. **Graceful Degradation**: If enhanced parsing fails, basic data is still returned

```python
# Example: Only process episodes if you need them
details = await anidb_details(aid)

if need_episode_info and details['episodes']:
    process_episodes(details['episodes'])

if need_character_info and details['characters']:
    process_characters(details['characters'])
```
