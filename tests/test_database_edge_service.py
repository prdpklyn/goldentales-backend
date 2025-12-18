# tests/test_database_edge_service.py
"""
Tests for Database Edge Service (Edge Function-based database operations).
"""

import pytest
from tests.fixtures.edge_functions import mock_database_edge_service


@pytest.mark.asyncio
async def test_create_story(mock_database_edge_service):
    """Test creating a story via Edge Function."""
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    assert story["id"] is not None
    assert story["child_name"] == "Emma"
    assert story["child_age"] == 6
    assert story["theme"] == "christmas"
    assert "created_at" in story


@pytest.mark.asyncio
async def test_get_story(mock_database_edge_service):
    """Test retrieving a story via Edge Function."""
    # Create a story first
    created_story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    # Retrieve it
    story = await mock_database_edge_service.get_story(created_story["id"])
    
    assert story is not None
    assert story["id"] == created_story["id"]
    assert story["child_name"] == "Emma"


@pytest.mark.asyncio
async def test_get_story_not_found(mock_database_edge_service):
    """Test retrieving a non-existent story."""
    story = await mock_database_edge_service.get_story("non-existent-id")
    
    assert story is None


@pytest.mark.asyncio
async def test_update_story(mock_database_edge_service):
    """Test updating a story via Edge Function."""
    # Create a story first
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    # Update it
    updated = await mock_database_edge_service.update_story(
        story["id"],
        {"status": "ready"}
    )
    
    assert updated is not None
    assert updated["status"] == "ready"


@pytest.mark.asyncio
async def test_create_page(mock_database_edge_service):
    """Test creating a page via Edge Function."""
    # Create a story first
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    # Create a page
    page = await mock_database_edge_service.create_page(
        story_id=story["id"],
        page_number=1,
        text_content="Once upon a time...",
        image_prompt="Emma in a snowy scene",
        image_url="https://example.com/image.jpg"
    )
    
    assert page["id"] is not None
    assert page["story_id"] == story["id"]
    assert page["page_number"] == 1
    assert page["text_content"] == "Once upon a time..."
    assert page["image_url"] == "https://example.com/image.jpg"


@pytest.mark.asyncio
async def test_get_pages(mock_database_edge_service):
    """Test retrieving pages via Edge Function."""
    # Create a story
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    # Create multiple pages
    for i in range(3):
        await mock_database_edge_service.create_page(
            story_id=story["id"],
            page_number=i + 1,
            text_content=f"Page {i + 1} text",
            image_prompt=f"Page {i + 1} prompt",
            image_url=f"https://example.com/page{i + 1}.jpg"
        )
    
    # Retrieve pages
    pages = await mock_database_edge_service.get_pages(story["id"])
    
    assert len(pages) == 3
    assert pages[0]["page_number"] == 1
    assert pages[1]["page_number"] == 2
    assert pages[2]["page_number"] == 3


@pytest.mark.asyncio
async def test_update_page(mock_database_edge_service):
    """Test updating a page via Edge Function."""
    # Create story and page
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    page = await mock_database_edge_service.create_page(
        story_id=story["id"],
        page_number=1,
        text_content="Original text",
        image_prompt="Original prompt",
        image_url="https://example.com/old.jpg"
    )
    
    # Update the page
    updated = await mock_database_edge_service.update_page(
        page["id"],
        {"image_url": "https://example.com/new.jpg"}
    )
    
    assert updated is not None
    assert updated["image_url"] == "https://example.com/new.jpg"


@pytest.mark.asyncio
async def test_get_page_by_number(mock_database_edge_service):
    """Test retrieving a specific page by number."""
    # Create story and pages
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    await mock_database_edge_service.create_page(
        story_id=story["id"],
        page_number=1,
        text_content="Page 1",
        image_prompt="Prompt 1"
    )
    
    await mock_database_edge_service.create_page(
        story_id=story["id"],
        page_number=2,
        text_content="Page 2",
        image_prompt="Prompt 2"
    )
    
    # Get specific page
    page = await mock_database_edge_service.get_page_by_number(story["id"], 2)
    
    assert page is not None
    assert page["page_number"] == 2
    assert page["text_content"] == "Page 2"


@pytest.mark.asyncio
async def test_get_full_book(mock_database_edge_service):
    """Test retrieving a complete book."""
    # Create story
    story = await mock_database_edge_service.create_story(
        child_name="Emma",
        child_age=6,
        theme="christmas"
    )
    
    # Create pages
    for i in range(10):
        await mock_database_edge_service.create_page(
            story_id=story["id"],
            page_number=i + 1,
            text_content=f"Page {i + 1}",
            image_prompt=f"Prompt {i + 1}",
            image_url=f"https://example.com/page{i + 1}.jpg"
        )
    
    # Get full book
    book = await mock_database_edge_service.get_full_book(story["id"])
    
    assert book is not None
    assert book["book_id"] == story["id"]
    assert len(book["pages"]) == 10
    assert len(book["preview_images"]) == 10
    assert book["page_count"] == 10
    assert "title" in book
    assert "character_bible" in book


@pytest.mark.asyncio
async def test_create_order(mock_database_edge_service):
    """Test creating an order via Edge Function."""
    order = await mock_database_edge_service.create_order({
        "story_id": "story-123",
        "format": "hardcover",
        "shipping_tier": "standard",
        "customer_email": "test@example.com"
    })
    
    assert order["id"] is not None
    assert order["story_id"] == "story-123"
    assert order["format"] == "hardcover"
    assert "created_at" in order


@pytest.mark.asyncio
async def test_get_order(mock_database_edge_service):
    """Test retrieving an order via Edge Function."""
    # Create an order
    created_order = await mock_database_edge_service.create_order({
        "story_id": "story-123",
        "format": "hardcover",
        "customer_email": "test@example.com"
    })
    
    # Retrieve it
    order = await mock_database_edge_service.get_order(created_order["id"])
    
    assert order is not None
    assert order["id"] == created_order["id"]
    assert order["format"] == "hardcover"


@pytest.mark.asyncio
async def test_update_order(mock_database_edge_service):
    """Test updating an order via Edge Function."""
    # Create an order
    order = await mock_database_edge_service.create_order({
        "story_id": "story-123",
        "format": "hardcover",
        "status": "pending"
    })
    
    # Update it
    updated = await mock_database_edge_service.update_order(
        order["id"],
        {"status": "completed"}
    )
    
    assert updated is not None
    assert updated["status"] == "completed"


@pytest.mark.asyncio
async def test_edge_function_error_handling(mock_database_edge_service):
    """Test error handling for Edge Function operations."""
    # Try to update non-existent story
    result = await mock_database_edge_service.update_story(
        "non-existent-id",
        {"status": "ready"}
    )
    
    assert result is None
    
    # Try to get pages for non-existent story
    pages = await mock_database_edge_service.get_pages("non-existent-id")
    
    assert pages == []

