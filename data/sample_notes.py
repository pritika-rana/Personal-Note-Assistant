"""
Sample data for testing the personal assistant
Real-world examples of notes, tasks, and queries
"""

from datetime import datetime, timedelta

NOW = datetime.now()
TOMORROW_MEETING = (NOW + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
NEXT_FRIDAY_MEETING = (NOW + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
END_OF_WEEK = NOW + timedelta(days=5)
REMINDER_NEXT_WEEK = NOW + timedelta(days=7)
MOMS_BIRTHDAY = datetime(2025, 6, 15)
DOCTOR_APPOINTMENT = datetime(2024, 11, 15, 10, 30)

# Sample notes to store in the vector database
SAMPLE_NOTES = [
    # Events
    {
        "text": "Meeting with Sarah from Marketing tomorrow at 3pm to discuss Q4 campaign",
        "metadata": {
            "note_type": "event",
            "date": TOMORROW_MEETING.isoformat(),
            "date_epoch": TOMORROW_MEETING.timestamp(),
            "timestamp": NOW.isoformat(),
            "has_future_date": True,
            "entities": {"people": ["Sarah"], "locations": [], "organizations": ["Marketing"]},
            "keywords": ["meeting", "discuss", "campaign"]
        }
    },
    {
        "text": "Doctor appointment on November 15th at 10:30am for annual checkup",
        "metadata": {
            "note_type": "event",
            "date": DOCTOR_APPOINTMENT.isoformat(),
            "date_epoch": DOCTOR_APPOINTMENT.timestamp(),
            "timestamp": NOW.isoformat(),
            "has_future_date": DOCTOR_APPOINTMENT > NOW,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["doctor", "appointment", "checkup", "annual"]
        }
    },
    {
        "text": "Conference call with the Tokyo office next Friday at 9am regarding new product launch",
        "metadata": {
            "note_type": "event",
            "date": NEXT_FRIDAY_MEETING.isoformat(),
            "date_epoch": NEXT_FRIDAY_MEETING.timestamp(),
            "timestamp": NOW.isoformat(),
            "has_future_date": True,
            "entities": {"people": [], "locations": ["Tokyo"], "organizations": []},
            "keywords": ["conference", "product", "launch"]
        }
    },
    
    # Tasks
    {
        "text": "Need to order new HDMI cables for the conference room",
        "metadata": {
            "note_type": "task",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["need", "order", "cables", "conference", "task"]
        }
    },
    {
        "text": "Finish the quarterly report by end of this week and send to manager",
        "metadata": {
            "note_type": "task",
            "date": END_OF_WEEK.isoformat(),
            "date_epoch": END_OF_WEEK.timestamp(),
            "timestamp": NOW.isoformat(),
            "has_future_date": True,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["finish", "quarterly", "report", "manager"]
        }
    },
    {
        "text": "Book flight tickets to San Francisco for the tech conference in December",
        "metadata": {
            "note_type": "task",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": [], "locations": ["San Francisco"], "organizations": []},
            "keywords": ["flight", "tickets", "conference"]
        }
    },
    
    # Personal Facts
    {
        "text": "Mom's birthday is on June 15th. She loves chocolate cake and gardening",
        "metadata": {
            "note_type": "fact",
            "date": MOMS_BIRTHDAY.isoformat(),
            "date_epoch": MOMS_BIRTHDAY.timestamp(),
            "timestamp": NOW.isoformat(),
            "has_future_date": MOMS_BIRTHDAY > NOW,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["birthday", "chocolate", "gardening"]
        }
    },
    {
        "text": "My sister Emma works at Google in Mountain View as a Software Engineer",
        "metadata": {
            "note_type": "fact",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": ["Emma"], "locations": ["Mountain View"], "organizations": ["Google"]},
            "keywords": ["works", "software", "engineer"]
        }
    },
    {
        "text": "Favorite restaurant is Pasta Palace on Main Street. Their carbonara is amazing",
        "metadata": {
            "note_type": "fact",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": [], "locations": ["Main Street"], "organizations": []},
            "keywords": ["favorite", "restaurant", "carbonara", "amazing"]
        }
    },
    {
        "text": "Gym membership number is 45678. Goes to FitLife Gym on weekday mornings",
        "metadata": {
            "note_type": "fact",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": [], "locations": [], "organizations": ["FitLife Gym"]},
            "keywords": ["membership", "number", "weekday", "mornings"]
        }
    },
    
    # Reminders
    {
        "text": "Remind me to call the dentist next week to schedule a cleaning",
        "metadata": {
            "note_type": "reminder",
            "date": REMINDER_NEXT_WEEK.isoformat(),
            "date_epoch": REMINDER_NEXT_WEEK.timestamp(),
            "timestamp": NOW.isoformat(),
            "has_future_date": True,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["remind", "dentist", "schedule", "cleaning"]
        }
    },
    {
        "text": "Remember to water the plants every Monday and Thursday",
        "metadata": {
            "note_type": "reminder",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["remember", "water", "plants", "monday", "thursday"]
        }
    },
    
    # General notes
    {
        "text": "Interesting book recommendation from John: 'Atomic Habits' by James Clear",
        "metadata": {
            "note_type": "general",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": ["John", "James Clear"], "locations": [], "organizations": []},
            "keywords": ["interesting", "recommendation", "atomic", "habits"]
        }
    },
    {
        "text": "Random thought: Should explore more outdoor hiking trails this summer",
        "metadata": {
            "note_type": "general",
            "date": None,
            "date_epoch": None,
            "timestamp": NOW.isoformat(),
            "has_future_date": False,
            "entities": {"people": [], "locations": [], "organizations": []},
            "keywords": ["random", "thought", "explore", "outdoor", "hiking", "trails", "summer"]
        }
    }
]

# Sample queries to test the system
SAMPLE_QUERIES = [
    # Retrieval queries
    "When is my doctor appointment?",
    "What meetings do I have this week?",
    "When is mom's birthday?",
    "Where does my sister work?",
    "What's my favorite restaurant?",
    "What do I need to buy at the grocery store?",
    
    # Date-based queries
    "What do I have scheduled tomorrow?",
    "Show me all events next week",
    "What tasks do I need to complete?",
    
    # Fact recall
    "Tell me about Emma",
    "What's my gym membership number?",
    "What book did John recommend?",
    
    # Multi-turn context
    "What do I have coming up?",
    "Any reminders for next week?",
]

# Expected answers for evaluation
EXPECTED_ANSWERS = {
    "When is my doctor appointment?": {
        "should_contain": ["November 15", "10:30"],
        "note_type": "event"
    },
    "When is mom's birthday?": {
        "should_contain": ["June 15"],
        "note_type": "fact"
    },
    "Where does my sister work?": {
        "should_contain": ["Google", "Mountain View"],
        "note_type": "fact"
    },
    "What do I need to buy at the grocery store?": {
        "should_contain": ["milk", "eggs", "bread"],
        "note_type": "task"
    }
}
