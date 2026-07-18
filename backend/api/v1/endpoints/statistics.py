"""Statistics endpoints."""

from fastapi import APIRouter
from backend.database.base import sync_engine
from backend.models import Draw
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/summary")
async def get_summary():
    """Get overall statistics summary."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        total_draws = session.query(Draw).count()
        latest = session.query(Draw).order_by(Draw.draw_date.desc()).first()
        oldest = session.query(Draw).order_by(Draw.draw_date.asc()).first()
        
        # Calculate average jackpot
        from sqlalchemy import func
        avg_jackpot = session.query(func.avg(Draw.jackpot_amount)).scalar()
        
        return {
            "total_draws": total_draws,
            "latest_draw": latest.to_dict() if latest else None,
            "oldest_draw": oldest.to_dict() if oldest else None,
            "average_jackpot": float(avg_jackpot) if avg_jackpot else 0,
            "date_range": {
                "start": oldest.draw_date.isoformat() if oldest else None,
                "end": latest.draw_date.isoformat() if latest else None
            }
        }
    finally:
        session.close()

@router.get("/frequency")
async def get_frequency_analysis():
    """Get detailed frequency analysis."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        draws = session.query(Draw).all()
        
        # Number frequencies
        frequencies = {i: 0 for i in range(1, 50)}
        for draw in draws:
            if draw.numbers:
                for num in draw.numbers:
                    if 1 <= num <= 49:
                        frequencies[num] = frequencies.get(num, 0) + 1
        
        # Bonus frequencies
        bonus_freq = {i: 0 for i in range(1, 50)}
        for draw in draws:
            if draw.bonus and 1 <= draw.bonus <= 49:
                bonus_freq[draw.bonus] = bonus_freq.get(draw.bonus, 0) + 1
        
        # Sort frequencies
        sorted_freq = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
        sorted_bonus = sorted(bonus_freq.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "number_frequencies": dict(sorted_freq[:10]),  # Top 10
            "bonus_frequencies": dict(sorted_bonus[:10]),  # Top 10
            "most_frequent_number": sorted_freq[0] if sorted_freq else None,
            "least_frequent_number": sorted_freq[-1] if sorted_freq else None,
            "total_draws": len(draws)
        }
    finally:
        session.close()

@router.get("/randomness")
async def test_randomness():
    """Run randomness tests."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        draws = session.query(Draw).all()
        
        # Simple randomness test: Check if numbers are evenly distributed
        frequencies = {i: 0 for i in range(1, 50)}
        for draw in draws:
            if draw.numbers:
                for num in draw.numbers:
                    if 1 <= num <= 49:
                        frequencies[num] = frequencies.get(num, 0) + 1
        
        # Calculate expected frequency (uniform distribution)
        total_numbers = sum(frequencies.values())
        expected = total_numbers / 49
        
        # Chi-square test
        chi_square = 0
        for num in range(1, 50):
            observed = frequencies.get(num, 0)
            chi_square += ((observed - expected) ** 2) / expected
        
        return {
            "test_name": "Chi-Square Test for Uniformity",
            "chi_square": round(chi_square, 2),
            "degrees_of_freedom": 48,
            "expected_frequency": round(expected, 2),
            "is_uniform": chi_square < 67.5,  # Critical value at 95% confidence
            "total_numbers": total_numbers,
            "sample_size": len(draws)
        }
    finally:
        session.close()
