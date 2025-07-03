from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from app.schemas import BookingRequest, BookingResponse, CalendarStatsResponse, AvailabilityRequest
from app.booking_agent import AdvancedBookingAgent, Intent
from app.logging_config import logger
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, List
from pydantic import BaseModel
import pytz
import time
import re
from functools import wraps

router = APIRouter(tags=["booking"])

_agent_instance = None
_agent_error = None

# Optional API key header for basic authentication will add this feature later !! 
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

_REQUESTS_PER_MINUTE = 60
_RATE_LIMIT_SECONDS = 60 / _REQUESTS_PER_MINUTE
_last_request_times: Dict[str, float] = {}

def rate_limit():
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            client_ip = "default"
            if request:
                client_ip = request.client.host if request.client else "default"
            
            current_time = time.time()
            last_request = _last_request_times.get(client_ip, 0)
            
            if current_time - last_request < _RATE_LIMIT_SECONDS:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later."
                )
            
            _last_request_times[client_ip] = current_time
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_agent():
    """Dependency to get the booking agent instance"""
    global _agent_instance, _agent_error
    
    if _agent_instance is None:
        if _agent_error is not None:
            logger.error(f"Booking agent initialization failed previously: {_agent_error}")
            raise HTTPException(status_code=500, detail="Booking agent initialization failed")
        
        try:
            logger.info("Initializing booking agent...")
            _agent_instance = AdvancedBookingAgent()
            logger.info("Booking agent initialized successfully")
        except Exception as e:
            _agent_error = str(e)
            logger.error(f"Failed to initialize booking agent: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize booking agent: {e}")
    
    return _agent_instance

async def get_api_key(api_key: str = Depends(api_key_header)):
    """Optional API key validation"""
    # Will add this later
    return api_key

@router.post("/book")
@rate_limit()
async def book_meeting(
    request: BookingRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):
    """Book a meeting with advanced NLP processing"""
    try:
        logger.info(f"Processing booking request: {request.message}")
        
        if not hasattr(agent, 'run'):
            raise HTTPException(status_code=500, detail="Booking agent not properly initialized")
        
        response = await asyncio.to_thread(agent.run, request.message)
        logger.info(f"Booking request processed successfully")
        
        event_id = None
        event_time = None
        success = False
        
        if response:
            response_lower = response.lower()
            success = any(phrase in response_lower for phrase in [
                "successfully booked", "booking confirmed", "meeting scheduled",
                "appointment created", "event added"
            ])
            
            time_patterns = [
                r"(\w+,\s+\w+\s+\d+\s+at\s+\d+:\d+\s*[AP]M)",
                r"(\w+\s+at\s+\d+:\d+\s*[AP]M)",
                r"(\d+:\d+\s*[AP]M\s+on\s+\w+)"
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, response, re.IGNORECASE)
                if time_match:
                    event_time = time_match.group(1)
                    break
        
        return BookingResponse(
            message=response or "Request processed",
            success=success,
            event_id=event_id,
            event_time=event_time
        )
        
    except asyncio.TimeoutError:
        logger.error("Booking request timed out")
        raise HTTPException(status_code=408, detail="Request timed out. Please try again.")
    except Exception as e:
        logger.error(f"Error processing booking request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process booking request: {str(e)}")

@router.post("/availability")
@rate_limit()
async def check_availability(
    request: AvailabilityRequest,
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):
    """Check availability for a time range"""
    try:
        logger.info(f"Processing availability check: {request.message}")
        
        if not hasattr(agent, 'run'):
            raise HTTPException(status_code=500, detail="Booking agent not properly initialized")
        
        response = await asyncio.to_thread(agent.run, request.message)
        logger.info("Availability check processed successfully")
        
        return BookingResponse(
            message=response or "Availability checked",
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check availability: {str(e)}")

@router.get("/meetings")
@rate_limit()
async def list_meetings(
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):
    """List upcoming meetings"""
    try:
        logger.info("Processing list meetings request")
        
        if not hasattr(agent, 'run'):
            raise HTTPException(status_code=500, detail="Booking agent not properly initialized")
        
        response = await asyncio.to_thread(agent.run, "list my meetings")
        logger.info("Listed upcoming meetings successfully")
        
        meetings = []
        if response and "upcoming meetings" in response.lower():
            lines = response.split("\n")
            for line in lines:
                patterns = [
                    r"(\d+)\.\s*\*\*(.*?)\*\*.*?📅\s*(.*?)(?:\n|⏱️|$).*?⏱️.*?(\d+)",
                    r"(\d+)\.\s*(.*?)\s*-\s*(.*?)\s*\((\d+)\s*min"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line, re.DOTALL | re.IGNORECASE)
                    if match:
                        try:
                            meetings.append({
                                "id": match.group(1),
                                "summary": match.group(2).strip(),
                                "start_time": match.group(3).strip(),
                                "duration": int(match.group(4)) if match.group(4).isdigit() else 60
                            })
                            break
                        except (IndexError, ValueError) as e:
                            logger.warning(f"Failed to parse meeting line: {line}, error: {e}")
                            continue
        
        return {
            "meetings": meetings,
            "total": len(meetings),
            "message": response or "No meetings found"
        }
        
    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list meetings: {str(e)}")

@router.delete("/meetings")
@rate_limit()
async def cancel_meeting(
    request: BookingRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):  
    """Cancel a meeting"""
    try:
        logger.info(f"Processing cancel meeting request: {request.message}")
        
        if not hasattr(agent, 'run'):
            raise HTTPException(status_code=500, detail="Booking agent not properly initialized")
        
        response = await asyncio.to_thread(agent.run, request.message)
        logger.info("Cancel meeting request processed successfully")
        
        success = False
        if response:
            response_lower = response.lower()
            success = any(phrase in response_lower for phrase in [
                "successfully cancelled", "cancelled", "meeting canceled",
                "appointment cancelled", "event removed"
            ])
        
        return BookingResponse(
            message=response or "Cancellation processed",
            success=success
        )
        
    except Exception as e:
        logger.error(f"Error cancelling meeting: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel meeting: {str(e)}")

@router.patch("/meetings")
@rate_limit()
async def reschedule_meeting(
    request: BookingRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):
    """Reschedule a meeting"""
    try:
        logger.info(f"Processing reschedule meeting request: {request.message}")
        
        if not hasattr(agent, 'run'):
            raise HTTPException(status_code=500, detail="Booking agent not properly initialized")
        
        response = await asyncio.to_thread(agent.run, request.message)
        logger.info("Reschedule meeting request processed successfully")
        
        success = False
        if response:
            response_lower = response.lower()
            success = any(phrase in response_lower for phrase in [
                "successfully rescheduled", "rescheduled", "meeting moved",
                "appointment rescheduled", "event updated"
            ])
        
        return BookingResponse(
            message=response or "Reschedule processed",
            success=success
        )
        
    except Exception as e:
        logger.error(f"Error rescheduling meeting: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reschedule meeting: {str(e)}")

@router.get("/stats")
@rate_limit()
async def get_calendar_stats(
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):
    """Get calendar statistics"""
    try:
        logger.info("Processing calendar stats request")
        
        if not hasattr(agent, 'calendar_service'):
            logger.warning("Calendar service not available, returning mock stats")
            return CalendarStatsResponse(
                total_meetings=0,
                upcoming_meetings=0,
                busy_hours_today=0,
                free_hours_today=8
            )
        
        stats = await asyncio.to_thread(agent.calendar_service.get_calendar_stats)
        logger.info("Retrieved calendar statistics successfully")
        return CalendarStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}")
        return CalendarStatsResponse(
            total_meetings=0,
            upcoming_meetings=0,
            busy_hours_today=0,
            free_hours_today=8
        )

@router.post("/preferences")
@rate_limit()
async def set_preferences(
    request: dict,
    http_request: Request,
    agent: AdvancedBookingAgent = Depends(get_agent)
):
    """Set user preferences (timezone, business hours, etc.)"""
    try:
        logger.info("Processing set preferences request")
        
        if not hasattr(agent, 'set_user_preferences'):
            raise HTTPException(status_code=500, detail="Preferences feature not available")
        
        timezone = request.get("timezone")
        business_hours_start = request.get("business_hours_start")
        business_hours_end = request.get("business_hours_end")
        default_duration = request.get("default_duration")
        
        business_hours = None
        if business_hours_start and business_hours_end:
            try:
                start_time = datetime.strptime(business_hours_start, "%H:%M").time()
                end_time = datetime.strptime(business_hours_end, "%H:%M").time()
                business_hours = (start_time, end_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid business hours format. Use HH:MM")
        
        await asyncio.to_thread(
            agent.set_user_preferences,
            timezone=timezone,
            business_hours=business_hours,
            default_duration=default_duration
        )
        
        logger.info("Preferences updated successfully")
        return BookingResponse(
            message="Preferences updated successfully",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set preferences: {str(e)}")

@router.get("/agent/health")
async def agent_health_check(agent: AdvancedBookingAgent = Depends(get_agent)):
    """Check if the booking agent is properly initialized and working"""
    try:
        if hasattr(agent, 'run'):
            test_response = await asyncio.to_thread(agent.run, "hello")
            return {
                "status": "healthy",
                "agent_initialized": True,
                "test_response_received": bool(test_response),
                "agent_type": type(agent).__name__
            }
        else:
            return {
                "status": "unhealthy",
                "agent_initialized": False,
                "error": "Agent missing run method"
            }
    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        return {
            "status": "unhealthy",
            "agent_initialized": False,
            "error": str(e)
        }