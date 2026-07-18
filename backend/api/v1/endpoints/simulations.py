"""Simulation endpoints."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import random
from datetime import datetime
from sqlalchemy.orm import sessionmaker

from backend.database.base import sync_engine
from backend.models import Draw, SimulationRun, Ticket

router = APIRouter()

class SimulationRequest(BaseModel):
    strategy_id: int
    num_tickets: int = 1000
    game_type: str = "6/49"  # "6/49" or "dailygrand"
    parameters: Optional[dict] = None

class SimulationResponse(BaseModel):
    id: int
    strategy_id: int
    total_tickets: int
    status: str
    game_type: str
    message: str

def generate_random_ticket_649():
    """Generate a random Lotto 6/49 ticket (6 numbers)."""
    return sorted(random.sample(range(1, 50), 6))

def generate_random_ticket_dailygrand():
    """Generate a random Daily Grand ticket (5 numbers + grand)."""
    numbers = sorted(random.sample(range(1, 50), 5))
    grand = random.randint(1, 7)
    return numbers, grand

def check_ticket_649(ticket_numbers, draws):
    """Check a Lotto 6/49 ticket against all historical draws."""
    best_match = 0
    prize_amount = 0
    
    for draw in draws:
        matched = len(set(ticket_numbers) & set(draw.numbers))
        if matched > best_match:
            best_match = matched
    
    prize_map = {3: 10, 4: 100, 5: 1000, 6: 1000000}
    prize_amount = prize_map.get(best_match, 0)
    
    return {'matches': best_match, 'prize_amount': prize_amount}

def check_ticket_dailygrand(ticket_numbers, grand_number, draws):
    """Check a Daily Grand ticket against all historical draws."""
    best_match = 0
    prize_amount = 0
    grand_match = False
    
    for draw in draws:
        # Get main numbers (first 5)
        main_numbers = draw.get_main_numbers()
        matched = len(set(ticket_numbers) & set(main_numbers))
        
        # Check grand number
        draw_grand = draw.get_grand_number()
        if draw_grand == grand_number:
            grand_match = True
        
        if matched > best_match:
            best_match = matched
    
    # Daily Grand prize structure
    if best_match == 5 and grand_match:
        prize_amount = 1000000  # $1,000/day for life
    elif best_match == 5:
        prize_amount = 25000   # $25,000/year for life
    elif best_match == 4 and grand_match:
        prize_amount = 1000
    elif best_match == 4:
        prize_amount = 500
    elif best_match == 3 and grand_match:
        prize_amount = 100
    elif best_match == 3:
        prize_amount = 20
    elif best_match == 2 and grand_match:
        prize_amount = 10
    elif best_match == 1 and grand_match:
        prize_amount = 4
    elif best_match == 0 and grand_match:
        prize_amount = 0  # Free play in real lottery
    
    return {'matches': best_match, 'prize_amount': prize_amount, 'grand_match': grand_match}

def run_simulation_task(simulation_id, strategy_id, num_tickets, game_type):
    """Background task to run simulation."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        # Update status
        sim = session.query(SimulationRun).filter(SimulationRun.id == simulation_id).first()
        if sim:
            sim.status = "running"
            sim.started_at = datetime.utcnow()
            sim.game_type = game_type
            session.commit()
        
        # Get draws for the specific game type
        draws = session.query(Draw).filter(Draw.lottery_type == 
            ("6/49" if game_type == "6/49" else "Daily Grand")).all()
        
        tickets = []
        total_cost = num_tickets * 3
        total_won = 0
        best_win = 0
        win_counts = {}
        
        if game_type == "6/49":
            win_counts = {3: 0, 4: 0, 5: 0, 6: 0}
            for i in range(num_tickets):
                numbers = generate_random_ticket_649()
                result = check_ticket_649(numbers, draws)
                
                ticket = Ticket(
                    simulation_run_id=simulation_id,
                    numbers=numbers,
                    matched_count=result['matches'],
                    prize_amount=result['prize_amount'],
                    was_winner=1 if result['matches'] >= 3 else 0
                )
                tickets.append(ticket)
                
                total_won += result['prize_amount']
                if result['matches'] >= 3:
                    win_counts[result['matches']] = win_counts.get(result['matches'], 0) + 1
                
                if result['prize_amount'] > best_win:
                    best_win = result['prize_amount']
        else:
            # Daily Grand
            win_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for i in range(num_tickets):
                numbers, grand = generate_random_ticket_dailygrand()
                result = check_ticket_dailygrand(numbers, grand, draws)
                
                ticket = Ticket(
                    simulation_run_id=simulation_id,
                    numbers=numbers,
                    matched_count=result['matches'],
                    prize_amount=result['prize_amount'],
                    was_winner=1 if result['prize_amount'] > 0 else 0,
                    grand_number=grand
                )
                tickets.append(ticket)
                
                total_won += result['prize_amount']
                win_counts[result['matches']] = win_counts.get(result['matches'], 0) + 1
                
                if result['prize_amount'] > best_win:
                    best_win = result['prize_amount']
        
        # Save all tickets
        session.add_all(tickets)
        
        # Update simulation results
        roi = (total_won - total_cost) / total_cost * 100 if total_cost > 0 else 0
        
        if sim:
            sim.status = "completed"
            sim.completed_at = datetime.utcnow()
            sim.total_tickets = num_tickets
            sim.total_cost = total_cost
            sim.total_won = total_won
            sim.roi = roi
            sim.best_win = best_win
            session.commit()
        
        print(f"✅ Simulation {simulation_id} ({game_type}) completed!")
        print(f"  Tickets: {num_tickets}, ROI: {roi:.2f}%")
        print(f"  Wins: {win_counts}")
        
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        session.rollback()
        if sim:
            sim.status = "failed"
            session.commit()
    finally:
        session.close()

@router.get("/")
async def get_simulations():
    """Get all simulations."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        sims = session.query(SimulationRun).order_by(SimulationRun.id.desc()).limit(10).all()
        return {
            "simulations": [
                {
                    "id": s.id,
                    "strategy_id": s.strategy_id,
                    "total_tickets": s.total_tickets,
                    "total_cost": float(s.total_cost) if s.total_cost else 0,
                    "total_won": float(s.total_won) if s.total_won else 0,
                    "roi": float(s.roi) if s.roi else 0,
                    "best_win": float(s.best_win) if s.best_win else 0,
                    "status": s.status,
                    "game_type": s.game_type or "6/49",
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None
                }
                for s in sims
            ]
        }
    finally:
        session.close()

@router.post("/", response_model=SimulationResponse)
async def create_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """Create a new simulation."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        sim = SimulationRun(
            strategy_id=request.strategy_id,
            total_tickets=0,
            total_cost=0,
            total_won=0,
            status="pending",
            game_type=request.game_type,
            parameters=request.parameters or {}
        )
        session.add(sim)
        session.commit()
        session.refresh(sim)
        
        background_tasks.add_task(
            run_simulation_task,
            sim.id,
            request.strategy_id,
            request.num_tickets,
            request.game_type
        )
        
        return SimulationResponse(
            id=sim.id,
            strategy_id=request.strategy_id,
            total_tickets=request.num_tickets,
            status="pending",
            game_type=request.game_type,
            message=f"Simulation created with {request.num_tickets} tickets for {request.game_type}"
        )
    finally:
        session.close()

@router.get("/{simulation_id}")
async def get_simulation(simulation_id: int):
    """Get a specific simulation with results."""
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    
    try:
        sim = session.query(SimulationRun).filter(SimulationRun.id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        tickets = session.query(Ticket).filter(Ticket.simulation_run_id == simulation_id).all()
        
        win_counts = {}
        for ticket in tickets:
            key = ticket.matched_count
            win_counts[key] = win_counts.get(key, 0) + 1
        
        return {
            "id": sim.id,
            "strategy_id": sim.strategy_id,
            "total_tickets": sim.total_tickets,
            "total_cost": float(sim.total_cost) if sim.total_cost else 0,
            "total_won": float(sim.total_won) if sim.total_won else 0,
            "roi": float(sim.roi) if sim.roi else 0,
            "best_win": float(sim.best_win) if sim.best_win else 0,
            "status": sim.status,
            "game_type": sim.game_type or "6/49",
            "started_at": sim.started_at.isoformat() if sim.started_at else None,
            "completed_at": sim.completed_at.isoformat() if sim.completed_at else None,
            "win_counts": win_counts,
            "tickets": [
                {
                    "numbers": ticket.numbers,
                    "matched": ticket.matched_count,
                    "prize": float(ticket.prize_amount),
                    "grand_number": ticket.grand_number
                }
                for ticket in tickets[:10]
            ]
        }
    finally:
        session.close()
