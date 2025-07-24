# Google Calendar Authentication Guide

## Single-User vs Multi-User Authentication

### Current Single-User Flow (Problematic for Multi-User)

**How it works:**
1. **Setup**: Place `credentials.json` in `scheduler_agent_v1/`
2. **First run**: OAuth flow opens browser for user consent
3. **Token storage**: Single `token.pickle` file stores access/refresh tokens
4. **Subsequent runs**: Reuses stored tokens, refreshes when expired

**Problems for multiple users:**
- ❌ **Token collision**: All users overwrite same `token.pickle`
- ❌ **No user isolation**: Can't distinguish between users
- ❌ **OAuth conflicts**: Multiple users can't authenticate simultaneously
- ❌ **Security risk**: Users access each other's calendars

### Multi-User Architecture Solution

**Key Components:**
1. **User-specific token storage**: `user_tokens/token_{hash}.pickle`
2. **User isolation**: Each user gets separate authentication
3. **Port management**: Different OAuth ports per user
4. **Secure hashing**: User IDs hashed for privacy

## Authentication Flows

### Single-User Flow
```
User Request → 
  Load token.pickle → 
    If valid: Use existing tokens
    If expired: Refresh tokens  
    If missing: OAuth flow → Save to token.pickle
```

### Multi-User Flow  
```
User Request (with user_id) →
  Load user_tokens/token_{hash}.pickle →
    If valid: Use existing tokens
    If expired: Refresh tokens
    If missing: OAuth flow (unique port) → Save to user-specific file
```

## Implementation Comparison

### Single-User (`calendar_service.py`)
```python
# Fixed paths - no user separation
token_path = Path(__file__).parent / "token.pickle"
credentials_path = Path(__file__).parent / "credentials.json"

# Single authentication function
def authenticate_google_calendar():
    # No user context
```

### Multi-User (`multi_user_calendar_service.py`)
```python
# User-specific paths
def _get_user_token_path(self, user_id):
    user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
    return self.tokens_dir / f"token_{user_hash}.pickle"

# User-aware authentication
def authenticate_user(self, user_id):
    # Per-user OAuth flow with unique ports
```

## Integration with ADK Sessions

### Current Agent Setup
```python
APP_NAME = 'SCHEDULER-APP-v01'
USER_ID = 'MANISH'  # Hardcoded
SESSION_ID = 'ses_001'

# Single user context
session = asyncio.run(session_service.create_session(
    app_name=APP_NAME, 
    user_id=USER_ID, 
    session_id=SESSION_ID
))
```

### Multi-User Agent Setup
```python
# Dynamic user context from session
def get_schedule_for_session(user_id, session_id):
    calendar_service = MultiUserCalendarService()
    return calendar_service.get_user_schedule(user_id)

# Updated tool function
def get_current_schedule():
    # Get user_id from current session context
    user_id = get_current_user_id()  # From session
    return calendar_service.get_user_schedule(user_id)
```

## Security Considerations

### Token Security
- **User isolation**: Each user's tokens stored separately
- **Privacy**: User IDs hashed in filenames
- **Access control**: No cross-user token access possible

### OAuth Security
- **Unique ports**: Prevents OAuth flow conflicts
- **Session binding**: Tokens tied to specific user sessions
- **Revocation**: Per-user token revocation capability

## Production Deployment Options

### Option 1: File-Based Storage (Current)
```
scheduler_agent_v1/
├── credentials.json          # OAuth app credentials
├── user_tokens/             # User-specific tokens
│   ├── token_a1b2c3d4.pickle # User 1 tokens
│   ├── token_e5f6g7h8.pickle # User 2 tokens
│   └── ...
```

**Pros**: Simple, no external dependencies
**Cons**: Not scalable, file system dependent

### Option 2: Database Storage
```python
class DatabaseCalendarService:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def store_user_tokens(self, user_id, credentials):
        # Store encrypted tokens in database
    
    def load_user_tokens(self, user_id):
        # Load and decrypt tokens from database
```

**Pros**: Scalable, centralized, backup-friendly
**Cons**: Requires database setup, encryption complexity

### Option 3: Cloud Storage (Google Cloud/AWS)
```python
class CloudCalendarService:
    def __init__(self, storage_client):
        self.storage = storage_client
    
    def store_user_tokens(self, user_id, credentials):
        # Store in encrypted cloud storage
```

**Pros**: Highly scalable, managed backup
**Cons**: Cloud dependency, cost considerations

## Migration Path

### Step 1: Backward Compatibility
Keep existing single-user function with default user:
```python
def get_current_schedule(user_id="default"):
    return get_user_schedule(user_id)
```

### Step 2: Update Agent Integration
```python
# Extract user_id from ADK session
def get_current_schedule():
    user_id = get_session_user_id()  # From current session
    return calendar_service.get_user_schedule(user_id)
```

### Step 3: Production Scaling
Choose storage backend based on scale:
- **< 100 users**: File-based storage
- **100-10K users**: Database storage  
- **> 10K users**: Cloud storage with caching

## Testing Multi-User Setup

```python
# Test with multiple users
service = MultiUserCalendarService()

# User 1 authentication
user1_schedule = service.get_user_schedule("user_123")

# User 2 authentication (separate tokens)
user2_schedule = service.get_user_schedule("user_456")

# Verify isolation
assert user1_schedule != user2_schedule
```