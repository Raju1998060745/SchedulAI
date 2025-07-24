"""
Multi-user Google Calendar integration service for ScheduleAI.
Handles per-user authentication and calendar data retrieval.
"""

from datetime import datetime, timedelta
import os.path
import pickle
import hashlib
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class MultiUserCalendarService:
    """Handles Google Calendar authentication and access for multiple users."""
    
    def __init__(self, base_path=None):
        """
        Initialize the calendar service.
        
        Args:
            base_path (str, optional): Base directory for storing user tokens
        """
        self.base_path = Path(base_path) if base_path else Path(__file__).parent
        self.credentials_path = self.base_path / "credentials.json"
        self.tokens_dir = self.base_path / "user_tokens"
        
        # Create tokens directory if it doesn't exist
        self.tokens_dir.mkdir(exist_ok=True)
    
    def _get_user_token_path(self, user_id):
        """
        Get the token file path for a specific user.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            Path: Path to user's token file
        """
        # Hash user_id for privacy and filename safety
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return self.tokens_dir / f"token_{user_hash}.pickle"
    
    def authenticate_user(self, user_id):
        """
        Authenticate a specific user with Google Calendar API.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            tuple: (credentials, error_message)
        """
        creds = None
        token_path = self._get_user_token_path(user_id)
        
        # Load existing token for this user
        if token_path.exists():
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                return None, f"Failed to load user token: {str(e)}"
        
        # Check if credentials are valid or need refresh
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    return None, f"Failed to refresh credentials for user {user_id}: {str(e)}"
            else:
                # Check if credentials.json exists
                if not self.credentials_path.exists():
                    return None, (
                        f"Google Calendar credentials.json not found at {self.credentials_path}. "
                        "Please download from Google Cloud Console."
                    )
                
                try:
                    # Run OAuth flow for this user
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES)
                    
                    # Use different port for each user to avoid conflicts
                    port = hash(user_id) % 1000 + 8000  # Port range: 8000-8999
                    creds = flow.run_local_server(port=port)
                    
                except Exception as e:
                    return None, f"OAuth flow failed for user {user_id}: {str(e)}"
            
            # Save credentials for this user
            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                return None, f"Failed to save credentials for user {user_id}: {str(e)}"
        
        return creds, None
    
    def get_user_calendar_events(self, user_id, start_date=None, end_date=None):
        """
        Retrieve calendar events for a specific user.
        
        Args:
            user_id (str): Unique user identifier
            start_date (datetime, optional): Start date for events
            end_date (datetime, optional): End date for events
            
        Returns:
            tuple: (events_list, error_message)
        """
        try:
            # Authenticate user
            creds, auth_error = self.authenticate_user(user_id)
            if auth_error:
                return None, auth_error
            
            if not creds:
                return None, f"Authentication failed for user {user_id}"
            
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
            return None, f"Google Calendar API error for user {user_id}: {error}"
        except Exception as e:
            return None, f"Unexpected error for user {user_id}: {str(e)}"
    
    def get_user_schedule(self, user_id):
        """
        Get formatted schedule for a specific user.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            str: Formatted schedule string or error message
        """
        try:
            # Get today's events for this user
            events, error = self.get_user_calendar_events(user_id)
            
            if error:
                return f"Calendar access error for user {user_id}: {error}"
            
            if events is None:
                return f"Failed to retrieve calendar events for user {user_id}."
            
            # Format events
            if not events:
                date_display = datetime.now().strftime('%Y-%m-%d')
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
            
            date_display = datetime.now().strftime('%Y-%m-%d')
            return f"Schedule for {date_display}:\n" + "\n".join(schedule_items)
            
        except Exception as e:
            return f"Unexpected error retrieving schedule for user {user_id}: {str(e)}"
    
    def revoke_user_access(self, user_id):
        """
        Revoke access and delete stored tokens for a user.
        
        Args:
            user_id (str): Unique user identifier
            
        Returns:
            tuple: (success, message)
        """
        try:
            token_path = self._get_user_token_path(user_id)
            
            if token_path.exists():
                # Load and revoke the token
                try:
                    with open(token_path, 'rb') as token:
                        creds = pickle.load(token)
                    
                    # Revoke the token with Google
                    if creds and creds.valid:
                        creds.revoke(Request())
                except Exception as e:
                    # Continue with deletion even if revocation fails
                    pass
                
                # Delete the token file
                token_path.unlink()
                return True, f"Access revoked for user {user_id}"
            else:
                return True, f"No stored credentials found for user {user_id}"
                
        except Exception as e:
            return False, f"Failed to revoke access for user {user_id}: {str(e)}"

# Global instance for backward compatibility
_calendar_service = MultiUserCalendarService()

def get_user_schedule(user_id):
    """
    Wrapper function to get schedule for a specific user.
    
    Args:
        user_id (str): Unique user identifier
        
    Returns:
        str: Formatted schedule string
    """
    return _calendar_service.get_user_schedule(user_id)

def get_current_schedule(user_id="default"):
    """
    Backward compatibility wrapper.
    
    Args:
        user_id (str): User identifier, defaults to "default"
        
    Returns:
        str: Formatted schedule string
    """
    return get_user_schedule(user_id)