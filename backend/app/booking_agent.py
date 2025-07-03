from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableSequence
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.calendar_service import EnhancedCalendarService
from app.config import Config
from app.logging_config import logger
from datetime import datetime, timedelta, time
import dateutil.parser
import re
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pytz
from dataclasses import dataclass

class Intent(Enum):
    BOOK_MEETING = "book_meeting"
    CHECK_AVAILABILITY = "check_availability"
    RESCHEDULE_MEETING = "reschedule_meeting"
    CANCEL_MEETING = "cancel_meeting"
    LIST_MEETINGS = "list_meetings"
    GREETING = "greeting"
    UNCLEAR = "unclear"

@dataclass
class ConversationContext:
    """Maintains conversation state and context"""
    user_id: str = "default_user"
    last_intent: Optional[Intent] = None
    pending_booking: Optional[Dict] = None
    conversation_history: List[Dict] = None
    user_timezone: str = "Asia/Kolkata"
    preferred_meeting_duration: int = 60
    business_hours_start: time = time(9, 0)
    business_hours_end: time = time(17, 0)
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []

@dataclass
class ParsedBookingRequest:
    """Structured representation of a booking request"""
    intent: Intent
    summary: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: int = 60
    attendees: List[str] = None
    description: Optional[str] = None
    meeting_type: str = "meeting"
    urgency: str = "normal"
    flexibility: str = "rigid"  
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

class AdvancedBookingAgent:
    """Industry-grade AI booking agent with advanced NLP and scheduling capabilities"""
    
    def __init__(self):
        try:
            Config.validate()
            self.llm = ChatOpenAI(
                api_key=Config.LLM_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                model="deepseek/deepseek-r1:free",
                temperature=0.3
            )
            self.calendar_service = EnhancedCalendarService()
            self.context = ConversationContext()
            self._setup_llm_chains()
            logger.info("Advanced booking agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize booking agent: {e}")
            raise

    def _setup_llm_chains(self):
        """Setup LangChain chains for different tasks"""
        
        # Intent recognition chain
        intent_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert at understanding user intentions for calendar booking requests.
Analyze the user's message and determine their intent.

Possible intents:
- book_meeting: User wants to schedule a new meeting
- check_availability: User wants to know available time slots
- reschedule_meeting: User wants to change an existing meeting
- cancel_meeting: User wants to cancel a meeting
- list_meetings: User wants to see their scheduled meetings
- greeting: User is greeting or making small talk
- unclear: Intent is not clear

Respond with just the intent name (e.g., "book_meeting")."""),
            HumanMessage(content="User message: {{user_input}}\nPrevious context: {{context}}")
        ])
        self.intent_chain = intent_prompt | self.llm
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Extract booking details from the user's message. Be intelligent about parsing times, dates, and contexts.

User message: "{user_input}"
Current date/time: {current_datetime}
User timezone: {timezone}
Previous context: {context}

Extract and return a JSON object with these fields:
{
    "summary": "meeting title/type",
    "start_time": "ISO datetime or null",
    "duration_minutes": number,
    "attendees": ["email1", "email2"],
    "description": "additional details",
    "meeting_type": "meeting/call/appointment/interview",
    "urgency": "low/normal/high/urgent",
    "flexibility": "rigid/flexible/very_flexible"
}

Time parsing rules:
- "tomorrow" = next day
- "next week" = same day next week
- "monday" = next occurrence of Monday
- "in 2 hours" = 2 hours from now
- "end of week" = Friday
- Handle AM/PM, 24-hour format, relative times

If time is ambiguous, set start_time to null.
Default duration is 60 minutes unless specified."""),
            HumanMessage(content="User message: {user_input}\nCurrent date/time: {current_datetime}\nUser timezone: {timezone}\nPrevious context: {context}")
        ])
        self.extraction_chain = extraction_prompt | self.llm
        
        response_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a friendly, professional AI scheduling assistant. Generate a natural, helpful response.

Situation: {situation}
User message: {user_input}
Agent action: {agent_action}
Result: {result}
Context: {context}

Generate a conversational response that:
1. Acknowledges the user's request
2. Explains what happened
3. Provides next steps if needed
4. Asks for clarification if required
5. Maintains a helpful, professional tone

Keep responses concise but informative."""),
            HumanMessage(content="Situation: {situation}\nUser message: {user_input}\nAgent action: {agent_action}\nResult: {result}\nContext: {context}")
        ])
        self.response_chain = response_prompt | self.llm

    def _recognize_intent(self, user_input: str) -> Intent:
        """Recognize user intent using LLM"""
        try:
            context_str = json.dumps({
                "last_intent": self.context.last_intent.value if self.context.last_intent else None,
                "has_pending_booking": self.context.pending_booking is not None,
                "recent_messages": self.context.conversation_history[-3:] if self.context.conversation_history else []
            })
            
            intent_result = self.intent_chain.invoke({
                "user_input": user_input,
                "context": context_str
            }).content.strip().lower()
            
            intent_mapping = {
                "book_meeting": Intent.BOOK_MEETING,
                "check_availability": Intent.CHECK_AVAILABILITY,
                "reschedule_meeting": Intent.RESCHEDULE_MEETING,
                "cancel_meeting": Intent.CANCEL_MEETING,
                "list_meetings": Intent.LIST_MEETINGS,
                "greeting": Intent.GREETING,
                "unclear": Intent.UNCLEAR
            }
            
            return intent_mapping.get(intent_result, Intent.UNCLEAR)
            
        except Exception as e:
            logger.error(f"Error recognizing intent: {e}")
            return Intent.UNCLEAR

    def _extract_booking_details(self, user_input: str) -> ParsedBookingRequest:
        """Extract detailed booking information using advanced NLP"""
        try:
            current_datetime = datetime.now(pytz.timezone(self.context.user_timezone))
            context_str = json.dumps({
                "last_booking": self.context.pending_booking,
                "preferences": {
                    "default_duration": self.context.preferred_meeting_duration,
                    "business_hours": f"{self.context.business_hours_start} - {self.context.business_hours_end}"
                }
            })
            
            extraction_result = self.extraction_chain.invoke({
                "user_input": user_input,
                "current_datetime": current_datetime.isoformat(),
                "timezone": self.context.user_timezone,
                "context": context_str
            }).content
            
            # Parse JSON response
            try:
                details = json.loads(extraction_result)
            except json.JSONDecodeError:
                # Fallback to regex parsing if LLM doesn't return valid JSON
                return self._fallback_parsing(user_input)
            
            start_time = None
            if details.get("start_time"):
                try:
                    start_time = dateutil.parser.parse(details["start_time"])
                    if start_time.tzinfo is None:
                        start_time = pytz.timezone(self.context.user_timezone).localize(start_time)
                except:
                    start_time = None
            
            return ParsedBookingRequest(
                intent=Intent.BOOK_MEETING,
                summary=details.get("summary", "Meeting"),
                start_time=start_time,
                duration=details.get("duration_minutes", self.context.preferred_meeting_duration),
                attendees=details.get("attendees", []),
                description=details.get("description", ""),
                meeting_type=details.get("meeting_type", "meeting"),
                urgency=details.get("urgency", "normal"),
                flexibility=details.get("flexibility", "rigid")
            )
            
        except Exception as e:
            logger.error(f"Error extracting booking details: {e}")
            return self._fallback_parsing(user_input)

    def _fallback_parsing(self, user_input: str) -> ParsedBookingRequest:
        """Fallback parsing using regex when LLM fails"""
        user_input_lower = user_input.lower()
        
        summary = "Meeting"
        if "interview" in user_input_lower:
            summary = "Interview"
        elif "call" in user_input_lower:
            summary = "Call"
        elif "appointment" in user_input_lower:
            summary = "Appointment"
        elif "standup" in user_input_lower:
            summary = "Standup"
        
        duration = self.context.preferred_meeting_duration
        duration_patterns = [
            r'(\d+)\s*(?:hour|hr)s?',
            r'(\d+)\s*(?:minute|min)s?',
            r'(\d+)\s*h\s*(\d+)\s*m'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                if len(match.groups()) == 1:
                    num = int(match.group(1))
                    if 'hour' in pattern or 'hr' in pattern:
                        duration = num * 60
                    else:
                        duration = num
                else:  # hour + minute format
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    duration = hours * 60 + minutes
                break
        
        start_time = self._parse_time_advanced(user_input_lower)
        
        return ParsedBookingRequest(
            intent=Intent.BOOK_MEETING,
            summary=summary,
            start_time=start_time,
            duration=duration,
            flexibility="flexible" if any(word in user_input_lower for word in ["flexible", "around", "roughly"]) else "rigid"
        )

    def _parse_time_advanced(self, user_input: str) -> Optional[datetime]:
        """Advanced time parsing with support for relative dates and fuzzy matching"""
        now = datetime.now(pytz.timezone(self.context.user_timezone))
        
        # Relative time patterns
        relative_patterns = [
            (r'in (\d+) (?:hour|hr)s?', lambda m: now + timedelta(hours=int(m.group(1)))),
            (r'in (\d+) (?:minute|min)s?', lambda m: now + timedelta(minutes=int(m.group(1)))),
            (r'tomorrow at (\d{1,2}):?(\d{2})?\s*(am|pm)?', self._parse_tomorrow_time),
            (r'next (\w+)', self._parse_next_weekday),
            (r'(\w+) at (\d{1,2}):?(\d{2})?\s*(am|pm)?', self._parse_weekday_time),
            (r'at (\d{1,2}):?(\d{2})?\s*(am|pm)?', self._parse_today_time),
            (r'(\d{1,2}):?(\d{2})?\s*(am|pm)', self._parse_today_time),
            (r'end of (?:the )?week', lambda m: self._get_end_of_week()),
            (r'beginning of (?:the )?week', lambda m: self._get_beginning_of_week()),
            (r'next week same time', lambda m: now + timedelta(weeks=1))
        ]
        
        for pattern, parser in relative_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                try:
                    return parser(match)
                except:
                    continue
        
        return None

    def _parse_tomorrow_time(self, match) -> datetime:
        """Parse 'tomorrow at X' patterns"""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        
        if ampm:
            if ampm.lower() == 'pm' and hour != 12:
                hour += 12
            elif ampm.lower() == 'am' and hour == 12:
                hour = 0
        
        tomorrow = datetime.now(pytz.timezone(self.context.user_timezone)) + timedelta(days=1)
        return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_today_time(self, match) -> datetime:
        """Parse 'at X' or 'X am/pm' patterns for today"""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3) if len(match.groups()) >= 3 else None
        
        if ampm:
            if ampm.lower() == 'pm' and hour != 12:
                hour += 12
            elif ampm.lower() == 'am' and hour == 12:
                hour = 0
        
        today = datetime.now(pytz.timezone(self.context.user_timezone))
        target_time = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if target_time <= today:
            target_time += timedelta(days=1)
        
        return target_time

    def _parse_next_weekday(self, match) -> datetime:
        """Parse 'next Monday' patterns"""
        weekday_name = match.group(1).lower()
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
        }
        
        if weekday_name not in weekdays:
            return None
        
        target_weekday = weekdays[weekday_name]
        now = datetime.now(pytz.timezone(self.context.user_timezone))
        days_ahead = target_weekday - now.weekday()
        
        if days_ahead <= 0:  
            days_ahead += 7
        
        target_date = now + timedelta(days=days_ahead)
        return target_date.replace(
            hour=self.context.business_hours_start.hour,
            minute=self.context.business_hours_start.minute,
            second=0, microsecond=0
        )

    def _parse_weekday_time(self, match) -> datetime:
        """Parse 'Monday at 3pm' patterns"""
        weekday_name = match.group(1).lower()
        hour = int(match.group(2))
        minute = int(match.group(3)) if match.group(3) else 0
        ampm = match.group(4)
        
        if ampm:
            if ampm.lower() == 'pm' and hour != 12:
                hour += 12
            elif ampm.lower() == 'am' and hour == 12:
                hour = 0
        
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
        }
        
        if weekday_name not in weekdays:
            return None
        
        target_weekday = weekdays[weekday_name]
        now = datetime.now(pytz.timezone(self.context.user_timezone))
        days_ahead = target_weekday - now.weekday()
        
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        elif days_ahead == 0:  # Today - check if time has passed
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                days_ahead = 7
        
        target_date = now + timedelta(days=days_ahead)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _get_end_of_week(self) -> datetime:
        """Get end of current week (Friday 5 PM)"""
        now = datetime.now(pytz.timezone(self.context.user_timezone))
        days_until_friday = 4 - now.weekday()  # Friday is weekday 4
        if days_until_friday < 0:
            days_until_friday += 7
        
        friday = now + timedelta(days=days_until_friday)
        return friday.replace(
            hour=self.context.business_hours_end.hour,
            minute=self.context.business_hours_end.minute,
            second=0, microsecond=0
        )

    def _get_beginning_of_week(self) -> datetime:
        """Get beginning of next week (Monday 9 AM)"""
        now = datetime.now(pytz.timezone(self.context.user_timezone))
        days_until_monday = 7 - now.weekday()
        monday = now + timedelta(days=days_until_monday)
        return monday.replace(
            hour=self.context.business_hours_start.hour,
            minute=self.context.business_hours_start.minute,
            second=0, microsecond=0
        )

    def _check_business_hours(self, dt: datetime) -> bool:
        """Check if datetime falls within business hours"""
        time_of_day = dt.time()
        return self.context.business_hours_start <= time_of_day <= self.context.business_hours_end

    def _suggest_alternative_times(self, requested_time: datetime, duration: int, flexibility: str) -> List[datetime]:
        """Suggest alternative time slots when requested time is busy"""
        suggestions = []
        
        if flexibility == "very_flexible":
            search_days = 14
            time_increments = [30, 60, 120]  # 30min, 1hr, 2hr intervals
        elif flexibility == "flexible":
            search_days = 7
            time_increments = [30, 60]
        else:  # rigid
            search_days = 2
            time_increments = [30]
        
        base_time = requested_time
        
        for day_offset in range(search_days):
            current_day = base_time + timedelta(days=day_offset)
            
            # Only suggest times within business hours
            start_time = current_day.replace(
                hour=self.context.business_hours_start.hour,
                minute=self.context.business_hours_start.minute
            )
            end_time = current_day.replace(
                hour=self.context.business_hours_end.hour,
                minute=self.context.business_hours_end.minute
            )
            
            current_time = start_time
            while current_time + timedelta(minutes=duration) <= end_time:
                if self.calendar_service.check_availability(current_time, duration):
                    suggestions.append(current_time)
                    if len(suggestions) >= 5:  
                        return suggestions
                
                increment = time_increments[0] if day_offset == 0 else time_increments[-1]
                current_time += timedelta(minutes=increment)
        
        return suggestions

    def _handle_booking_request(self, request: ParsedBookingRequest) -> str:
        """Handle a booking request with intelligent scheduling"""
        try:
            if not request.start_time:
                return self._generate_response(
                    "unclear_time",
                    f"I'd be happy to book a {request.summary.lower()} for you! Could you please specify when you'd like to schedule it? You can say things like 'tomorrow at 3pm', 'next Monday at 10am', or 'in 2 hours'.",
                    request
                )
            
            if not self._check_business_hours(request.start_time):
                return self._generate_response(
                    "outside_business_hours",
                    f"The requested time ({request.start_time.strftime('%A, %B %d at %I:%M %p')}) is outside business hours ({self.context.business_hours_start.strftime('%I:%M %p')} - {self.context.business_hours_end.strftime('%I:%M %p')}). Would you like me to suggest times during business hours?",
                    request
                )
            
            if self.calendar_service.check_availability(request.start_time, request.duration):
                result = self.calendar_service.create_event(
                    request.summary,
                    request.start_time,
                    request.duration,
                    request.description
                )
                
                self.context.last_intent = Intent.BOOK_MEETING
                self.context.pending_booking = None
                
                return self._generate_response(
                    "booking_successful",
                    f"Perfect! I've successfully booked your {request.summary.lower()} for {request.start_time.strftime('%A, %B %d at %I:%M %p')} ({request.duration} minutes). You should receive a calendar invitation shortly.",
                    request
                )
            
            else:
                alternatives = self._suggest_alternative_times(
                    request.start_time, 
                    request.duration, 
                    request.flexibility
                )
                
                if alternatives:
                    self.context.pending_booking = request.__dict__
                    
                    alt_text = "\n".join([
                        f"• {alt.strftime('%A, %B %d at %I:%M %p')}"
                        for alt in alternatives[:3]
                    ])
                    
                    return self._generate_response(
                        "time_conflict_with_alternatives",
                        f"I'm sorry, but {request.start_time.strftime('%A, %B %d at %I:%M %p')} is already booked. Here are some available alternatives:\n\n{alt_text}\n\nWould any of these work for you? Just let me know which one you prefer!",
                        request
                    )
                else:
                    return self._generate_response(
                        "no_alternatives",
                        f"Unfortunately, {request.start_time.strftime('%A, %B %d at %I:%M %p')} is already booked, and I couldn't find any suitable alternatives in the next few days. Could you suggest a different time or date range?",
                        request
                    )
                    
        except Exception as e:
            logger.error(f"Error handling booking request: {e}")
            return "I encountered an error while processing your booking request. Please try again or contact support if the issue persists."

    def _handle_availability_check(self, user_input: str) -> str:
        """Handle availability check requests"""
        try:
            time_slots = self._extract_time_range(user_input)
            if not time_slots:
                return "I'd be happy to check your availability! Please specify a time range, like 'What's available tomorrow afternoon?' or 'Show me free slots next week'."
            
            available_slots = []
            for slot_start in time_slots:
                if self.calendar_service.check_availability(slot_start, self.context.preferred_meeting_duration):
                    available_slots.append(slot_start)
            
            if available_slots:
                slots_text = "\n".join([
                    f"• {slot.strftime('%A, %B %d at %I:%M %p')}"
                    for slot in available_slots[:10]  
                ])
                return f"Here are your available time slots:\n\n{slots_text}\n\nWould you like to book any of these times?"
            else:
                return "I don't see any available slots in the requested time range. Would you like me to check a different time period?"
                
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return "I encountered an error while checking availability. Please try again."

    def _extract_time_range(self, user_input: str) -> List[datetime]:
        """Extract time range for availability checks"""
        now = datetime.now(pytz.timezone(self.context.user_timezone))
        slots = []
        
        if "tomorrow" in user_input.lower():
            tomorrow = now + timedelta(days=1)
            start_time = tomorrow.replace(
                hour=self.context.business_hours_start.hour,
                minute=self.context.business_hours_start.minute
            )
            
            current = start_time
            end_of_day = tomorrow.replace(
                hour=self.context.business_hours_end.hour,
                minute=self.context.business_hours_end.minute
            )
            
            while current < end_of_day:
                slots.append(current)
                current += timedelta(hours=1)
        
        elif "next week" in user_input.lower():
            next_monday = now + timedelta(days=(7 - now.weekday()))
            for day in range(5):  
                day_start = (next_monday + timedelta(days=day)).replace(
                    hour=self.context.business_hours_start.hour,
                    minute=self.context.business_hours_start.minute
                )
                
                current = day_start
                day_end = day_start.replace(
                    hour=self.context.business_hours_end.hour,
                    minute=self.context.business_hours_end.minute
                )
                
                while current < day_end:
                    slots.append(current)
                    current += timedelta(hours=2)  
        
        return slots

    def _generate_response(self, situation: str, default_response: str, context_data=None) -> str:
        """Generate contextual responses using LLM"""
        try:
            context_str = json.dumps({
                "conversation_history": self.context.conversation_history[-3:],
                "user_timezone": self.context.user_timezone,
                "business_hours": f"{self.context.business_hours_start} - {self.context.business_hours_end}"
            })
            
            response = self.response_chain.invoke({
                "situation": situation,
                "user_input": self.context.conversation_history[-1]["user"] if self.context.conversation_history else "",
                "agent_action": situation,
                "result": default_response,
                "context": context_str
            }).content
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return default_response

    def run(self, user_input: str) -> str:
        """Main entry point for processing user requests"""
        try:
            self.context.conversation_history.append({
                "user": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            if len(self.context.conversation_history) > 10:
                self.context.conversation_history = self.context.conversation_history[-10:]
            
            intent = self._recognize_intent(user_input)
            logger.info(f"Recognized intent: {intent.value}")
            
            if intent == Intent.GREETING:
                response = "Hello! I'm your AI scheduling assistant. I can help you book meetings, check your availability, and manage your calendar. What would you like to do today?"
            
            elif intent == Intent.BOOK_MEETING:
                booking_request = self._extract_booking_details(user_input)
                response = self._handle_booking_request(booking_request)
            
            elif intent == Intent.CHECK_AVAILABILITY:
                response = self._handle_availability_check(user_input)
            
            elif intent == Intent.LIST_MEETINGS:
                response = self._handle_list_meetings()
            
            elif intent == Intent.CANCEL_MEETING:
                response = self._handle_cancel_meeting(user_input)
            
            elif intent == Intent.RESCHEDULE_MEETING:
                response = self._handle_reschedule_meeting(user_input)
            
            else:  # UNCLEAR or other
                response = self._handle_unclear_request(user_input)
            
            self.context.conversation_history[-1]["assistant"] = response
            self.context.last_intent = intent
            
            return response
            
        except Exception as e:
            logger.error(f"Error in main run method: {e}")
            return "I apologize, but I encountered an unexpected error. Please try rephrasing your request or contact support if the issue persists."

    def _handle_list_meetings(self) -> str:
        """Handle requests to list upcoming meetings"""
        try:
            upcoming_meetings = self.calendar_service.get_upcoming_events(limit=10)
            
            if not upcoming_meetings:
                return "You don't have any upcoming meetings scheduled. Would you like to book a new one?"
            
            meetings_text = "Here are your upcoming meetings:\n\n"
            for i, meeting in enumerate(upcoming_meetings, 1):
                start_time = meeting.get('start_time')
                title = meeting.get('summary', 'Untitled Meeting')
                duration = meeting.get('duration', 'Unknown duration')
                
                if start_time:
                    meetings_text += f"{i}. **{title}**\n   📅 {start_time.strftime('%A, %B %d at %I:%M %p')}\n   ⏱️ {duration} minutes\n\n"
            
            return meetings_text + "Would you like to reschedule or cancel any of these meetings?"
            
        except Exception as e:
            logger.error(f"Error listing meetings: {e}")
            return "I'm having trouble accessing your calendar right now. Please try again in a moment."

    def _handle_cancel_meeting(self, user_input: str) -> str:
        """Handle meeting cancellation requests"""
        try:
            meeting_info = self._extract_meeting_reference(user_input)
            
            if not meeting_info:
                return "I'd be happy to help cancel a meeting! Could you please specify which meeting you'd like to cancel? You can mention the time, title, or say something like 'cancel my 3pm meeting tomorrow'."
            
            cancelled = self.calendar_service.cancel_event(meeting_info)
            
            if cancelled:
                return f"I've successfully cancelled your meeting. You should receive a cancellation notification shortly."
            else:
                return "I couldn't find that meeting in your calendar. Could you please check the details and try again?"
                
        except Exception as e:
            logger.error(f"Error cancelling meeting: {e}")
            return "I encountered an error while trying to cancel the meeting. Please try again or contact support."

    def _handle_reschedule_meeting(self, user_input: str) -> str:
        """Handle meeting rescheduling requests"""
        try:
            meeting_info = self._extract_meeting_reference(user_input)
            new_time_info = self._extract_booking_details(user_input)
            
            if not meeting_info:
                return "I'd be happy to help reschedule a meeting! Please specify which meeting you'd like to reschedule and the new time. For example: 'reschedule my 3pm meeting to 4pm tomorrow'."
            
            if not new_time_info.start_time:
                self.context.pending_booking = {"action": "reschedule", "meeting": meeting_info}
                return f"I found the meeting you want to reschedule. What's the new time you'd prefer?"
            
            if self.calendar_service.check_availability(new_time_info.start_time, new_time_info.duration):
                success = self.calendar_service.reschedule_event(meeting_info, new_time_info.start_time, new_time_info.duration)
                
                if success:
                    return f"Perfect! I've rescheduled your meeting to {new_time_info.start_time.strftime('%A, %B %d at %I:%M %p')}. All attendees will be notified of the change."
                else:
                    return "I had trouble rescheduling the meeting. Please check the meeting details and try again."
            else:
                alternatives = self._suggest_alternative_times(new_time_info.start_time, new_time_info.duration, "flexible")
                if alternatives:
                    alt_text = "\n".join([f"• {alt.strftime('%A, %B %d at %I:%M %p')}" for alt in alternatives[:3]])
                    return f"The requested new time is not available. Here are some alternatives:\n\n{alt_text}\n\nWhich time works best for you?"
                else:
                    return "The requested time isn't available and I couldn't find suitable alternatives. Could you suggest a different time?"
                    
        except Exception as e:
            logger.error(f"Error rescheduling meeting: {e}")
            return "I encountered an error while trying to reschedule the meeting. Please try again."

    def _extract_meeting_reference(self, user_input: str) -> Optional[Dict]:
        """Extract meeting reference from user input for cancellation/rescheduling"""
        patterns = [
            r'(\d{1,2}:\d{2})\s*(am|pm)?',  
            r'(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',  
            r'meeting with (\w+)',  
            r'(\w+) meeting'  
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                return {"reference": match.group(0), "type": "pattern_match"}
        
        return None

    def _handle_unclear_request(self, user_input: str) -> str:
        """Handle unclear or ambiguous requests"""
        try:
            clarification_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""The user said: "{user_input}"

This is unclear in the context of calendar booking. Generate a helpful response that:
1. Acknowledges their input
2. Asks for clarification
3. Provides examples of what they can ask for
4. Maintains a friendly, helpful tone

Keep it concise and actionable."""),
                HumanMessage(content=user_input)
            ])
            
            response = self.llm.invoke(clarification_prompt).content.strip()
            return response
            
        except Exception as e:
            logger.error(f"Error handling unclear request: {e}")
            return """I'm not quite sure what you'd like me to help with. I can assist you with:

• **Booking meetings**: "Book a meeting tomorrow at 3pm"
• **Checking availability**: "What times are free this week?"
• **Viewing your schedule**: "Show me my meetings today"
• **Cancelling meetings**: "Cancel my 2pm meeting"
• **Rescheduling**: "Move my meeting to 4pm"

What would you like to do?"""

    def set_user_preferences(self, timezone: str = None, business_hours: Tuple[time, time] = None, 
                           default_duration: int = None):
        """Set user preferences for better personalization"""
        if timezone:
            self.context.user_timezone = timezone
        if business_hours:
            self.context.business_hours_start, self.context.business_hours_end = business_hours
        if default_duration:
            self.context.preferred_meeting_duration = default_duration
        
        logger.info(f"Updated user preferences: timezone={timezone}, business_hours={business_hours}, duration={default_duration}")

    def get_conversation_summary(self) -> Dict:
        """Get a summary of the current conversation context"""
        return {
            "last_intent": self.context.last_intent.value if self.context.last_intent else None,
            "has_pending_booking": self.context.pending_booking is not None,
            "conversation_length": len(self.context.conversation_history),
            "user_timezone": self.context.user_timezone,
            "business_hours": f"{self.context.business_hours_start} - {self.context.business_hours_end}"
        }