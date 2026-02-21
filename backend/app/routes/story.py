# AnCapTruyenLamVideo - Story Routes

from fastapi import APIRouter, HTTPException, status
from typing import List

from ..models.story import Story, StoryCreate, StoryUpdate
from ..services.story import StoryService

router = APIRouter(
    prefix="/api/stories",
    tags=["stories"],
    responses={404: {"description": "Story not found"}}
)


@router.get(
    "",
    response_model=List[dict],
    summary="Get all stories",
    description="Retrieve a list of all stories, sorted by creation date (newest first)."
)
async def get_stories():
    """Get all stories from the database."""
    stories = await StoryService.get_all()
    return stories


@router.get(
    "/{story_id}",
    response_model=dict,
    summary="Get a story by ID",
    description="Retrieve a single story by its unique identifier."
)
async def get_story(story_id: str):
    """Get a single story by its ID."""
    story = await StoryService.get_by_id(story_id)

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with ID '{story_id}' not found"
        )

    return story


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new story",
    description="Create a new story with the provided data."
)
async def create_story(story: StoryCreate):
    """Create a new story."""
    created_story = await StoryService.create(story)
    return created_story


@router.put(
    "/{story_id}",
    response_model=dict,
    summary="Update a story",
    description="Update an existing story. Only provided fields will be updated."
)
async def update_story(story_id: str, story: StoryUpdate):
    """Update an existing story."""
    # Check if story exists
    if not await StoryService.exists(story_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with ID '{story_id}' not found"
        )

    updated_story = await StoryService.update(story_id, story)

    if not updated_story:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update story"
        )

    return updated_story


@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a story",
    description="Delete a story by its unique identifier."
)
async def delete_story(story_id: str):
    """Delete a story from the database."""
    deleted = await StoryService.delete(story_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with ID '{story_id}' not found"
        )

    return None
