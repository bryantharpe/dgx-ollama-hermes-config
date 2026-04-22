#!/usr/bin/env python3
"""Pydantic models for AI World Fair API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ─── requests ───
class ScanContactRequest(BaseModel):
    raw_json: str


class CreateBookmarkRequest(BaseModel):
    entity_id: str
    type: str


class UpdateUserBookmarkRequest(BaseModel):
    entity_id: Optional[str] = None
    type: Optional[str] = None


# ─── responses ───
class Talk(BaseModel):
    id: int
    talk_id: str
    title: str
    abstract: Optional[str] = None
    speaker_id: Optional[int] = None
    start_time: str
    end_time: str
    room: Optional[str] = None
    track: Optional[str] = None
    tags: Optional[str] = None
    level: Optional[str] = None


class Speaker(BaseModel):
    id: int
    speaker_id: str
    name: str
    bio: Optional[str] = None
    github: Optional[str] = None
    twitter: Optional[str] = None
    company: Optional[str] = None


class Booth(BaseModel):
    id: int
    booth_id: str
    name: str
    category: Optional[str] = None
    grid_x: int
    grid_y: int
    description: Optional[str] = None
    website: Optional[str] = None


class Badge(BaseModel):
    name: str
    github: str
    topic: str


class Contact(BaseModel):
    id: int
    name: str
    github: Optional[str] = None
    topic: Optional[str] = None
    scanned_at: str
    raw_json: Optional[str] = None


class Bookmark(BaseModel):
    id: int
    talk_id: Optional[int] = None
    created_at: str
    type: str
    entity_id: str


# ─── collections ───
class TalkList(BaseModel):
    talks: List[Talk]


class SpeakerList(BaseModel):
    speakers: List[Speaker]


class BoothList(BaseModel):
    booths: List[Booth]


class ContactList(BaseModel):
    contacts: List[Contact]


class BookmarkList(BaseModel):
    bookmarks: List[Bookmark]


# ─── search results ───
class SearchResponse(BaseModel):
    query: str
    results: List[Talk]


# ─── route optimization ───
class RouteOptimizeRequest(BaseModel):
    booth_ids: List[str]
    start_x: Optional[int] = 0
    start_y: Optional[int] = 0


class RouteOptimizeResponse(BaseModel):
    route: List[str]
    total_distance: int
    path: List[List[int]]


# ─── responses ───
class HealthResponse(BaseModel):
    status: str


class DeleteResponse(BaseModel):
    deleted: int


class ScanContactResponse(BaseModel):
    id: int
    name: str
    github: Optional[str] = None
    topic: Optional[str] = None
    scanned_at: str
    raw_json: Optional[str] = None
