# AnCapTruyenLamVideo - Story Service

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from ..database import Database
from ..models.story import StoryCreate, StoryUpdate


class StoryService:
    """
    Service layer for Story CRUD operations.
    Handles all database interactions for stories.
    """

    COLLECTION_NAME = "stories"

    @classmethod
    def _get_collection(cls) -> AsyncIOMotorCollection:
        """Get the stories collection."""
        return Database.get_collection(cls.COLLECTION_NAME)

    @classmethod
    def _serialize_story(cls, story: dict) -> dict:
        """Convert MongoDB document to API-friendly format."""
        if story and "_id" in story:
            story["_id"] = str(story["_id"])
        return story

    @classmethod
    async def get_all(cls) -> List[dict]:
        """Get all stories from the database."""
        collection = cls._get_collection()
        stories = []

        cursor = collection.find().sort("createdAt", -1)
        async for story in cursor:
            stories.append(cls._serialize_story(story))

        return stories

    @classmethod
    async def get_by_id(cls, story_id: str) -> Optional[dict]:
        """Get a single story by its ID."""
        if not ObjectId.is_valid(story_id):
            return None

        collection = cls._get_collection()
        story = await collection.find_one({"_id": ObjectId(story_id)})

        if story:
            return cls._serialize_story(story)
        return None

    @classmethod
    async def create(cls, story_data: StoryCreate) -> dict:
        """Create a new story in the database."""
        collection = cls._get_collection()

        now = datetime.utcnow()
        story_dict = story_data.model_dump()
        story_dict["createdAt"] = now
        story_dict["updatedAt"] = now

        result = await collection.insert_one(story_dict)
        story_dict["_id"] = str(result.inserted_id)

        return story_dict

    @classmethod
    async def update(cls, story_id: str, story_data: StoryUpdate) -> Optional[dict]:
        """Update an existing story."""
        if not ObjectId.is_valid(story_id):
            return None

        collection = cls._get_collection()

        # Only include fields that are set (not None)
        update_dict = {
            k: v for k, v in story_data.model_dump().items()
            if v is not None
        }

        if not update_dict:
            # No fields to update, return existing story
            return await cls.get_by_id(story_id)

        # Always update the updatedAt timestamp
        update_dict["updatedAt"] = datetime.utcnow()

        result = await collection.find_one_and_update(
            {"_id": ObjectId(story_id)},
            {"$set": update_dict},
            return_document=True
        )

        if result:
            return cls._serialize_story(result)
        return None

    @classmethod
    async def delete(cls, story_id: str) -> bool:
        """Delete a story from the database."""
        if not ObjectId.is_valid(story_id):
            return False

        collection = cls._get_collection()
        result = await collection.delete_one({"_id": ObjectId(story_id)})

        return result.deleted_count > 0

    @classmethod
    async def exists(cls, story_id: str) -> bool:
        """Check if a story exists."""
        if not ObjectId.is_valid(story_id):
            return False

        collection = cls._get_collection()
        count = await collection.count_documents({"_id": ObjectId(story_id)})

        return count > 0
