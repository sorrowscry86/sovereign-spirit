"""
Message Model for User-Agent Bidirectional Communication

This model stores user messages and agent responses for the VoidCat Tether app.
Enables conversation history and interaction tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Message(Base):
    """
    SQLAlchemy model for storing messages.
    
    Attributes:
        id: Unique message identifier (UUID)
        sender: Who sent the message ('user' or 'agent')
        content: The message content/text
        timestamp: When the message was created
        agent_id: Which agent is involved in this conversation
        thought_id: Optional link to system_log entry for agent responses
    """
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender = Column(String, nullable=False)  # 'user' | 'agent'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    agent_id = Column(String, nullable=False)
    thought_id = Column(String, nullable=True)  # Link to system_log if applicable
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "thought_id": self.thought_id
        }
