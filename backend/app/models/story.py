# AnCapTruyenLamVideo - Story Model

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class StoryBase(BaseModel):
    """Base model for Story with common fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Story title")
    description: str = Field(default="", max_length=2000, description="Story description")
    author: str = Field(..., min_length=1, max_length=100, description="Story author")
    status: Literal["draft", "published", "archived"] = Field(
        default="draft",
        description="Story status"
    )


class StoryCreate(StoryBase):
    """Model for creating a new story."""
    pass


class StoryUpdate(BaseModel):
    """Model for updating an existing story. All fields are optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[Literal["draft", "published", "archived"]] = None


class StoryInDB(StoryBase):
    """Model representing a story as stored in the database."""
    id: str = Field(..., alias="_id", description="MongoDB ObjectId as string")
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Story(StoryBase):
    """Model for API responses."""
    _id: str = Field(..., description="MongoDB ObjectId as string")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
