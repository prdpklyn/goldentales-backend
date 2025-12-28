#!/usr/bin/env python3
"""
Debug script to diagnose story query issues.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import settings
from app.services.database import get_database
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def debug_story_query(story_id: str):
    """Debug why a story query is failing."""
    
    print("=" * 70)
    print("Story Query Debugger")
    print("=" * 70)
    print(f"\nStory ID: {story_id}")
    print(f"Story ID length: {len(story_id)}")
    print(f"Story ID format: {'Valid UUID' if len(story_id) == 36 else 'Invalid length'}")
    
    # Check configuration
    print("\n[1] Configuration Check:")
    print(f"  Supabase URL: {'✓' if settings.supabase_url else '✗'} {settings.supabase_url[:50] if settings.supabase_url else 'Not set'}...")
    print(f"  Supabase Key: {'✓' if settings.supabase_key else '✗'} {settings.supabase_key[:20] + '...' if settings.supabase_key else 'Not set'}")
    
    if not settings.supabase_url or not settings.supabase_key:
        print("\n❌ ERROR: Supabase credentials not configured!")
        return
    
    # Get database service
    print("\n[2] Database Service:")
    db = get_database()
    if not db.client:
        print("  ❌ Database client not initialized")
        return
    print("  ✓ Database client initialized")
    
    # Test 1: Can we query the table at all?
    print("\n[3] Testing Table Access:")
    try:
        # Try to get any stories
        result = db.client.table("stories").select("id, child_name, child_age").limit(5).execute()
        print(f"  ✓ Can query 'stories' table")
        print(f"  ✓ Found {len(result.data)} stories in table")
        
        if result.data:
            print("\n  Sample stories:")
            for i, story in enumerate(result.data[:5], 1):
                print(f"    {i}. ID: {story.get('id')}")
                print(f"       Name: {story.get('child_name')}")
                print(f"       Age: {story.get('child_age')}")
        
    except Exception as e:
        print(f"  ❌ Cannot query 'stories' table: {type(e).__name__}: {e}")
        print(f"     This might be a Row Level Security (RLS) issue")
        return
    
    # Test 2: Try exact match
    print(f"\n[4] Querying for Story ID: {story_id}")
    try:
        result = db.client.table("stories").select("*").eq("id", story_id).execute()
        
        if result.data:
            story = result.data[0]
            print(f"  ✓ Found story!")
            print(f"    ID: {story.get('id')}")
            print(f"    Child Name: {story.get('child_name')}")
            print(f"    Child Age: {story.get('child_age')}")
            print(f"    Theme: {story.get('theme')}")
            return story
        else:
            print(f"  ❌ Story not found with exact ID match")
            
    except Exception as e:
        print(f"  ❌ Query error: {type(e).__name__}: {e}")
    
    # Test 3: Try partial match (in case of typo)
    print(f"\n[5] Checking for similar IDs:")
    try:
        # Get all story IDs
        all_stories = db.client.table("stories").select("id, child_name").execute()
        
        # Check for partial matches
        story_id_short = story_id.replace("-", "")
        matches = []
        for story in all_stories.data:
            story_id_db = story.get('id', '')
            story_id_db_short = story_id_db.replace("-", "")
            
            # Check if they're similar
            if story_id_short in story_id_db_short or story_id_db_short in story_id_short:
                matches.append((story_id_db, story.get('child_name')))
        
        if matches:
            print(f"  ⚠️  Found {len(matches)} similar IDs:")
            for match_id, name in matches:
                print(f"    - {match_id} ({name})")
                if match_id == story_id:
                    print(f"      ✓ This is an exact match!")
        else:
            print(f"  No similar IDs found")
            
        # Show all IDs for reference
        print(f"\n  All story IDs in database ({len(all_stories.data)} total):")
        for i, story in enumerate(all_stories.data[:20], 1):
            sid = story.get('id', 'N/A')
            name = story.get('child_name', 'N/A')
            match = "✓ MATCH" if sid == story_id else ""
            print(f"    {i:2d}. {sid} ({name}) {match}")
        
        if len(all_stories.data) > 20:
            print(f"    ... and {len(all_stories.data) - 20} more")
            
    except Exception as e:
        print(f"  ❌ Error listing stories: {type(e).__name__}: {e}")
    
    # Test 4: Try alternative column names
    print(f"\n[6] Trying Alternative Column Names:")
    for col_name in ["story_id", "uuid", "_id"]:
        try:
            result = db.client.table("stories").select("*").eq(col_name, story_id).execute()
            if result.data:
                print(f"  ✓ Found using column '{col_name}'!")
                return result.data[0]
        except Exception as e:
            print(f"  ✗ Column '{col_name}': {type(e).__name__}")
    
    # Test 5: Try alternative table names
    print(f"\n[7] Trying Alternative Table Names:")
    for table_name in ["story", "books", "book"]:
        try:
            result = db.client.table(table_name).select("*").eq("id", story_id).execute()
            if result.data:
                print(f"  ✓ Found in table '{table_name}'!")
                return result.data[0]
        except Exception as e:
            print(f"  ✗ Table '{table_name}': {type(e).__name__}")
    
    print("\n" + "=" * 70)
    print("SUMMARY: Story not found with any method")
    print("=" * 70)
    print("\nPossible issues:")
    print("  1. Story ID is incorrect (check for typos)")
    print("  2. Row Level Security (RLS) blocking the query")
    print("  3. Table/column name mismatch")
    print("  4. Story exists in a different database/project")
    print("\nNext steps:")
    print("  1. Verify the story ID from Supabase dashboard")
    print("  2. Check RLS policies on 'stories' table")
    print("  3. Try using service_role key instead of publishable key")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug story query issues")
    parser.add_argument(
        "story_id",
        nargs="?",
        default="5eb41ff4-6d98-47d0-a6ed-af5a81222a42",
        help="Story ID to query"
    )
    
    args = parser.parse_args()
    
    asyncio.run(debug_story_query(args.story_id))










