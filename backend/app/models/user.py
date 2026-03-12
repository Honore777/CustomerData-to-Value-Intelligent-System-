"""
User Models
===========

User: Owner and Manager accounts
InviteToken: Invitation tokens for managers to join locations
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class User(Base):
    """
    Represents a user account (Owner or Manager).
    
    OWNER:
    - Creates Business during signup
    - Can invite managers to locations
    - Sees all locations aggregated
    - assigned_location_ids = None (means unlimited access)
    
    MANAGER:
    - Invited to specific location(s)
    - Can only see assigned locations
    - assigned_location_ids = [1, 2, 3]  (JSON array of location IDs)
    
    Both connected to a Business and can only access their business data.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    # Role-based access control
    role = Column(String(50), default="owner")  # "owner" or "manager"
    
    # Which locations can this user see? (JSON array of location IDs)
    # Owner: None (can see all)
    # Manager: [1, 2, 3] (can only see locations 1, 2, 3)
    assigned_location_ids = Column(JSON, nullable=True)  
    is_platform_admin = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business")
    
    __table_args__ = (
        Index("idx_email", "email"),
        Index("idx_business_role", "business_id", "role"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    


class InviteToken(Base):
    """
    Invitation token for managers to join locations.
    
    WORKFLOW:
    1. Owner invites manager: POST /locations/{loc_id}/invite-manager {email}
    2. System generates random token + expiration (7 days)
    3. System emails: "Click: domain/invite?token=abc123"
    4. Manager clicks link → sets password → User account created
    5. InviteToken marked as is_used=True
    
    Allows one-time secure invitations without exposing passwords.
    """
    __tablename__ = "invite_tokens"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    token = Column(String(255), nullable=False, unique=True)  # Random string (like uuid4)
    is_used = Column(Boolean, default=False)  # Mark as used after account creation
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Expires in 7 days from creation
    
    __table_args__ = (
        Index("idx_token", "token"),
        Index("idx_email_location", "email", "location_id"),
    )
    
    def __repr__(self):
        return f"<InviteToken(email={self.email}, location_id={self.location_id})>"
