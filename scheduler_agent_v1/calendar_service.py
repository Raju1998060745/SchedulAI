"""
Google Calendar integration service for ScheduleAI.
Handles authentication and calendar data retrieval.
"""

from datetime import datetime, timedelta
import os.path
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def authenticate_google_calendar():
    """
    Authenticate with Google Calendar API.
    
    Returns:
        tuple: (credentials, error_message)
    """
    creds = None
    token_path = Path(__file__).parent / "token.pickle"
    credentials_path = Path(__file__).parent / "credentials.json"
    
    # Load existing token if available
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # Check if credentials are valid or need refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                return None, f"Failed to refresh credentials: {str(e)}"
        else:
            # Check if credentials.json exists
            if not credentials_path.exists():
                return None, (
                    "Google Calendar credentials.json not found. "
                    "Please download from Google Cloud Console and place in scheduler_agent_v1/ directory."
                )
            
            try:
                # Run OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                return None, f"OAuth flow failed: {str(e)}"
        
        # Save credentials for future use
        try:
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            return None, f"Failed to save credentials: {str(e)}"
    
    return creds, None

def get_calendar_events(start_date=None, end_date=None):
    """
    Retrieve calendar events from Google Calendar.
    
    Args:
        start_date (datetime, optional): Start date for events. Defaults to today's start.
        end_date (datetime, optional): End date for events. Defaults to today's end.
    
    Returns:
        tuple: (events_list, error_message)
    """
    try:
        # Authenticate
        creds, auth_error = authenticate_google_calendar()
        if auth_error:
            return None, auth_error
        
        if not creds:
            return None, "Authentication failed - no valid credentials"
        
        # Build the service
        service = build('calendar', 'v3', credentials=creds)
        
        # Set default date range (today)
        if start_date is None:
            now = datetime.now()
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            start_date = start_date if start_date else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events, None
        
    except HttpError as error:
        return None, f"Google Calendar API error: {error}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def format_calendar_events(events, date_str=None):
    """
    Format calendar events into a readable string.
    
    Args:
        events (list): List of calendar events from Google Calendar API
        date_str (str, optional): Date string for display. Defaults to today.
    
    Returns:
        str: Formatted schedule string
    """
    if not events:
        date_display = date_str or datetime.now().strftime('%Y-%m-%d')
        return f"No events scheduled for {date_display}."
    
    schedule_items = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', 'No title')
        location = event.get('location', '')
        
        # Format time for display
        if 'T' in start:  # dateTime format (timed event)
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            time_str = start_time.strftime("%I:%M %p")
        else:  # all-day event
            time_str = "All day"
        
        # Add location if available
        event_str = f"{summary} at {time_str}"
        if location:
            event_str += f" ({location})"
        
        schedule_items.append(event_str)
    
    date_display = date_str or datetime.now().strftime('%Y-%m-%d')
    return f"Current schedule for {date_display}:\n" + "\n".join(schedule_items)

def get_current_schedule():
    """
    Get the current day's schedule from Google Calendar.
    
    Returns:
        str: Formatted schedule string or error message
    """
    try:
        # Get today's events
        events, error = get_calendar_events()
        
        if error:
            return f"Calendar access error: {error}"
        
        if events is None:
            return "Failed to retrieve calendar events."
        
        # Format and return the schedule
        return format_calendar_events(events)
        
    except Exception as e:
        return f"Unexpected error retrieving schedule: {str(e)}"