# Google Calendar Integration Setup

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Google Cloud Console Setup:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials
   - Download `credentials.json` file

3. **Place credentials:**
   - Save `credentials.json` in `scheduler_agent_v1/` directory

## Authentication Flow

1. **First run:** Browser will open for OAuth consent
2. **Token storage:** `token.pickle` will be created for future use
3. **Automatic refresh:** Token refreshes when expired

## Features

- **Real-time calendar:** Fetches today's events from primary Google Calendar
- **Time formatting:** Displays events with proper time format
- **All-day events:** Handles both timed and all-day events
- **Fallback:** Uses mock data if Calendar API fails
- **Error handling:** Graceful degradation with informative messages

## Security Notes

- `credentials.json` contains client secrets - keep secure
- `token.pickle` contains user tokens - exclude from git
- Add both files to `.gitignore`

## Usage

The `get_current_schedule()` function now:
1. Authenticates with Google Calendar
2. Fetches today's events (12:00 AM to 11:59 PM)
3. Formats events with times
4. Returns formatted schedule string

## Troubleshooting

- **"credentials.json not found":** Download from Google Cloud Console
- **Authentication errors:** Delete `token.pickle` and re-authenticate
- **Permission denied:** Check Calendar API is enabled
- **No events:** Function returns "Current schedule is empty for today"