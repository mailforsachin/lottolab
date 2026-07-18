"""Draw endpoints."""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.database.base import get_async_session
from backend.models import Draw
from sqlalchemy.orm import sessionmaker
from backend.database.base import sync_engine

router = APIRouter()

@router.get("/")
async def get_draws(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get all draws with pagination."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        draws = session.query(Draw).offset(offset).limit(limit).all()
        total = session.query(Draw).count()
        
        return {
            "draws": [draw.to_dict() for draw in draws],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    finally:
        session.close()

@router.get("/{draw_id}")
async def get_draw(draw_id: int):
    """Get a specific draw by ID."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        draw = session.query(Draw).filter(Draw.id == draw_id).first()
        if not draw:
            raise HTTPException(status_code=404, detail="Draw not found")
        return draw.to_dict()
    finally:
        session.close()

@router.get("/stats/frequencies")
async def get_frequencies():
    """Get number frequency analysis."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        draws = session.query(Draw).all()
        frequencies = {i: 0 for i in range(1, 50)}
        
        for draw in draws:
            if draw.numbers:
                for num in draw.numbers:
                    if 1 <= num <= 49:
                        frequencies[num] = frequencies.get(num, 0) + 1
        
        # Sort by frequency (descending)
        sorted_freq = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "frequencies": dict(sorted_freq),
            "most_frequent": sorted_freq[0] if sorted_freq else None,
            "least_frequent": sorted_freq[-1] if sorted_freq else None,
            "total_draws": len(draws)
        }
    finally:
        session.close()
