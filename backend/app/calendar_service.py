from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from app.config import Config
from app.logging_config import logger
import os
import pytz
from typing import List, Dict, Optional, Tuple
import hashlib
import time
from functools import lru_cache
from dataclasses import dataclass

SCOPES = ['https://www.googleapis.com/auth/calendar']

@dataclass
class CalendarEvent:
    """Structured representation of a calendar event"""
    id: str
    summary: str
    start_time: datetime
    end_time: datetime
    description: str = ""
    attendees: List[str] = None
    location: str = ""
    status: str = "confirmed"
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

class EnhancedCalendarService:
    """Enhanced calendar service with advanced features and optimizations"""
    
    def __init__(self):
        try:
            if not os.path.exists(Config.SERVICE_ACCOUNT_FILE):
                raise FileNotFoundError(f"Service account file not found: {Config.SERVICE_ACCOUNT_FILE}")
            
            credentials = service_account.Credentials.from_service_account_file(
                Config.SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            self.service = build('calendar', 'v3', credentials=credentials)
            
            self._events_cache = {}
            self._cache_expiry = {}
            self._cache_duration = 300  # 5 minutes
            
            self._last_request_time = 0
            self._min_request_interval = 0.1  # 100ms between requests
            
            logger.info("Enhanced calendar service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize calendar service: {e}")
            raise

    def _rate_limit(self):
        """Implement rate limiting to avoid API quota issues"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()

    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key for method calls"""
        key_data = f"{method}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache_expiry:
            return False
        return time.time() < self._cache_expiry[cache_key]

    def _set_cache(self, cache_key: str, data):
        """Set cache with expiry time"""
        self._events_cache[cache_key] = data
        self._cache_expiry[cache_key] = time.time() + self._cache_duration

    @lru_cache(maxsize=100)
    def _parse_datetime(self, dt_string: str) -> datetime:
        """Parse datetime string with caching"""
        try:
            if 'T' in dt_string:
                return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            else:
                date_obj = datetime.fromisoformat(dt_string)
                return pytz.UTC.localize(date_obj)
        except Exception as e:
            logger.error(f"Error parsing datetime {dt_string}: {e}")
            return None

    def check_availability(self, start_time: datetime, duration_minutes: int, 
                          buffer_minutes: int = 0) -> bool:
        """
        Enhanced availability checking with buffer time and conflict detection
        
        Args:
            start_time: Proposed meeting start time
            duration_minutes: Meeting duration in minutes
            buffer_minutes: Buffer time before/after meetings (default: 0)
        """
        try:
            self._rate_limit()
            
            buffer_delta = timedelta(minutes=buffer_minutes)
            check_start = start_time - buffer_delta
            end_time = start_time + timedelta(minutes=duration_minutes)
            check_end = end_time + buffer_delta
            
            cache_key = self._get_cache_key(
                "check_availability",
                start=check_start.isoformat(),
                end=check_end.isoformat()
            )
            
            if self._is_cache_valid(cache_key):
                result = self._events_cache[cache_key]
                logger.info(f"Availability check (cached): {result}")
                return result
            
            events_result = self.service.events().list(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                timeMin=check_start.isoformat(),
                timeMax=check_end.isoformat(),
                singleEvents=True,
                orderBy='startTime',
                fields='items(id,summary,start,end,status)'
            ).execute()
            
            events = events_result.get('items', [])
            
            active_events = [
                event for event in events 
                if event.get('status', '').lower() != 'cancelled'
            ]
            
            is_available = len(active_events) == 0
            
            self._set_cache(cache_key, is_available)
            
            logger.info(f"Availability check for {start_time} ({duration_minutes}min): {'Available' if is_available else 'Busy'}")
            
            if not is_available:
                for event in active_events:
                    event_start = self._parse_datetime(event['start'].get('dateTime', event['start'].get('date')))
                    logger.info(f"Conflict with: {event.get('summary', 'Untitled')} at {event_start}")
            
            return is_available
            
        except HttpError as e:
            logger.error(f"Google Calendar API error in availability check: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False

    def create_event(self, summary: str, start_time: datetime, duration_minutes: int, 
                    description: str = "", attendees: List[str] = None, 
                    location: str = "", send_notifications: bool = True) -> str:
        """
        Enhanced event creation with rich metadata and notification options
        """
        try:
            self._rate_limit()
            
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event_data = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': start_time.tzinfo.zone if start_time.tzinfo else 'UTC'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': end_time.tzinfo.zone if end_time.tzinfo else 'UTC'
                },
                'status': 'confirmed'
            }
            
            if location:
                event_data['location'] = location
            
            if attendees:
                event_data['attendees'] = [{'email': email} for email in attendees]
            
            metadata = f"\n\n--- Event Details ---\nDuration: {duration_minutes} minutes\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\nCreated by: AI Scheduling Assistant"
            event_data['description'] = f"{description}{metadata}"
            
            created_event = self.service.events().insert(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                body=event_data,
                sendNotifications=send_notifications
            ).execute()
            
            self._clear_cache_for_timerange(start_time, end_time)
            
            event_link = created_event.get('htmlLink', '')
            message = f"✅ Successfully booked: {summary}\n📅 {start_time.strftime('%A, %B %d at %I:%M %p')}\n⏱️ Duration: {duration_minutes} minutes"
            
            if event_link:
                message += f"\n🔗 [View in Calendar]({event_link})"
            
            logger.info(f"Event created successfully: {created_event.get('id')}")
            return message
            
        except HttpError as e:
            error_msg = f"Google Calendar API error: {e}"
            logger.error(error_msg)
            return f" Failed to create event: {e.reason if hasattr(e, 'reason') else 'Unknown error'}"
        except Exception as e:
            error_msg = f"Failed to create event: {e}"
            logger.error(error_msg)
            return f" {error_msg}"

    def get_upcoming_events(self, limit: int = 10, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming events with rich formatting and metadata
        """
        try:
            self._rate_limit()
            
            now = datetime.now(pytz.UTC)
            future_time = now + timedelta(days=days_ahead)
            
            cache_key = self._get_cache_key(
                "upcoming_events",
                limit=limit,
                start=now.isoformat(),
                end=future_time.isoformat()
            )
            
            if self._is_cache_valid(cache_key):
                return self._events_cache[cache_key]
            
            events_result = self.service.events().list(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                timeMin=now.isoformat(),
                timeMax=future_time.isoformat(),
                maxResults=limit,
                singleEvents=True,
                orderBy='startTime',
                fields='items(id,summary,start,end,description,location,attendees,status)'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            
            for event in events:
                if event.get('status', '').lower() == 'cancelled':
                    continue
                
                start_dt = self._parse_datetime(
                    event['start'].get('dateTime', event['start'].get('date'))
                )
                end_dt = self._parse_datetime(
                    event['end'].get('dateTime', event['end'].get('date'))
                )
                
                if start_dt and end_dt:
                    duration = int((end_dt - start_dt).total_seconds() / 60)
                    
                    formatted_event = {
                        'id': event.get('id'),
                        'summary': event.get('summary', 'Untitled Meeting'),
                        'start_time': start_dt,
                        'end_time': end_dt,
                        'duration': duration,
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                        'attendees': [
                            attendee.get('email', '') 
                            for attendee in event.get('attendees', [])
                        ]
                    }
                    formatted_events.append(formatted_event)
            
            self._set_cache(cache_key, formatted_events)
            logger.info(f"Retrieved {len(formatted_events)} upcoming events")
            return formatted_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API error getting events: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []

    def cancel_event(self, event_reference: Dict) -> bool:
        """
        Cancel an event based on various reference criteria
        """
        try:
            self._rate_limit()
            
            event_id = self._find_event_by_reference(event_reference)
            
            if not event_id:
                logger.warning(f"Could not find event to cancel: {event_reference}")
                return False
            
            self.service.events().delete(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                eventId=event_id,
                sendNotifications=True
            ).execute()
            
            self._clear_all_caches()
            
            logger.info(f"Event cancelled successfully: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Google Calendar API error cancelling event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling event: {e}")
            return False

    def reschedule_event(self, event_reference: Dict, new_start_time: datetime, 
                        new_duration: int = None) -> bool:
        """
        Reschedule an existing event to a new time
        """
        try:
            self._rate_limit()
            
            event_id = self._find_event_by_reference(event_reference)
            
            if not event_id:
                logger.warning(f"Could not find event to reschedule: {event_reference}")
                return False
            
            existing_event = self.service.events().get(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            if new_duration:
                new_end_time = new_start_time + timedelta(minutes=new_duration)
            else:
                original_start = self._parse_datetime(
                    existing_event['start'].get('dateTime', existing_event['start'].get('date'))
                )
                original_end = self._parse_datetime(
                    existing_event['end'].get('dateTime', existing_event['end'].get('date'))
                )
                original_duration = original_end - original_start
                new_end_time = new_start_time + original_duration
            
            existing_event['start'] = {
                'dateTime': new_start_time.isoformat(),
                'timeZone': new_start_time.tzinfo.zone if new_start_time.tzinfo else 'UTC'
            }
            existing_event['end'] = {
                'dateTime': new_end_time.isoformat(),
                'timeZone': new_end_time.tzinfo.zone if new_end_time.tzinfo else 'UTC'
            }
            
            current_desc = existing_event.get('description', '')
            reschedule_note = f"\n\n--- Rescheduled ---\nMoved to: {new_start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\nRescheduled by: AI Scheduling Assistant"
            existing_event['description'] = f"{current_desc}{reschedule_note}"
            
            updated_event = self.service.events().update(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                eventId=event_id,
                body=existing_event,
                sendNotifications=True
            ).execute()
            
            self._clear_all_caches()
            
            logger.info(f"Event rescheduled successfully: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Google Calendar API error rescheduling event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error rescheduling event: {e}")
            return False

    def get_busy_times(self, start_time: datetime, end_time: datetime) -> List[Tuple[datetime, datetime]]:
        """
        Get all busy time slots in a given range
        """
        try:
            self._rate_limit()
            
            events = self.service.events().list(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            busy_times = []
            for event in events.get('items', []):
                if event.get('status', '').lower() == 'cancelled':
                    continue
                
                event_start = self._parse_datetime(
                    event['start'].get('dateTime', event['start'].get('date'))
                )
                event_end = self._parse_datetime(
                    event['end'].get('dateTime', event['end'].get('date'))
                )
                
                if event_start and event_end:
                    busy_times.append((event_start, event_end))
            
            return busy_times
            
        except Exception as e:
            logger.error(f"Error getting busy times: {e}")
            return []

    def _find_event_by_reference(self, reference: Dict) -> Optional[str]:
        """
        Find an event ID based on various reference criteria
        This is a simplified implementation - can be enhanced with fuzzy matching
        """
        try:
            recent_events = self.get_upcoming_events(limit=50, days_ahead=7)
            
            reference_text = reference.get('reference', '').lower()
            
            for event in recent_events:
                if reference_text in event['summary'].lower():
                    return event['id']
                
                event_time_str = event['start_time'].strftime('%I:%M %p').lower()
                if reference_text in event_time_str:
                    return event['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding event by reference: {e}")
            return None

    def _clear_cache_for_timerange(self, start_time: datetime, end_time: datetime):
        """Clear cache entries that might be affected by changes in a time range"""
        
        keys_to_remove = [
            key for key in self._events_cache.keys() 
            if key.startswith('check_availability') or key.startswith('upcoming_events')
        ]
        
        for key in keys_to_remove:
            self._events_cache.pop(key, None)
            self._cache_expiry.pop(key, None)

    def _clear_all_caches(self):
        """Clear all caches"""
        self._events_cache.clear()
        self._cache_expiry.clear()

    def get_calendar_stats(self) -> Dict:
        """Get calendar statistics and health metrics"""
        try:
            now = datetime.now(pytz.UTC)
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=7)
            
            week_events = self.get_upcoming_events(limit=100, days_ahead=7)
            
            stats = {
                'total_events_this_week': len(week_events),
                'cache_hit_ratio': len(self._events_cache) / max(1, len(self._events_cache) + 1),
                'api_health': 'healthy',
                'last_update': now.isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting calendar stats: {e}")
            return {'api_health': 'error', 'error': str(e)}

    def cleanup_old_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry_time in self._cache_expiry.items()
            if current_time > expiry_time
        ]
        
        for key in expired_keys:
            self._events_cache.pop(key, None)
            self._cache_expiry.pop(key, None)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")