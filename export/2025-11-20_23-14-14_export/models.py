"""Data models for Soomgo chat scraper."""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ===== Chat List Models =====

class QuoteInfo(BaseModel):
    """Quote information for a chat"""
    id: int
    price: int
    is_hired: bool
    is_instantmatch: bool
    is_extra_pro: bool
    unit: str
    is_opened: bool
    is_reward: bool


class UserInfo(BaseModel):
    """User information"""
    id: int
    address: str
    is_leaved: bool
    name: str
    profile_image: Optional[str] = None
    is_certify_name: bool
    is_active: bool
    is_dormant: bool
    is_banned: bool
    is_soomgo_leaved: bool


class ServiceInfo(BaseModel):
    """Service information"""
    title: str


class AddressInfo(BaseModel):
    """Address information"""
    address1: str
    address2: str
    address3: Optional[str] = None


class RequestInfo(BaseModel):
    """Request information"""
    id: int
    is_targeted: bool
    object_id: str
    address: AddressInfo


class SafePaymentInfo(BaseModel):
    """Safe payment information"""
    safe_payment_id: int
    safe_payment_status: str


class ChatItem(BaseModel):
    """Individual chat item from the API response"""
    id: int
    quote: QuoteInfo
    user: UserInfo
    service: ServiceInfo
    request: RequestInfo
    is_favorite: bool
    last_message_type: str
    last_message: str
    created_at: str  # Will parse as datetime
    updated_at: str  # Will parse as datetime
    escrow: Optional[Any] = None
    new_message_count: int
    unlock: bool
    unlock_customer: bool
    role: str
    is_induce_customer: bool
    safe_payment: Optional[SafePaymentInfo] = None
    provider_message_count: int
    notification_status: bool


class ChatListResponse(BaseModel):
    """Response from the chat list API"""
    next: Optional[str] = None
    cursor: Optional[str] = None
    results: List[ChatItem]
    escrow_events_meta: List[Any] = Field(default_factory=list)


# ===== Chat Message Models =====

class MessageProviderInfo(BaseModel):
    """Provider information in a message"""
    id: Optional[int] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    has_business: Optional[bool] = None
    has_credentials: Optional[bool] = None
    has_escrow_account: Optional[bool] = None
    score: Optional[Dict[str, Any]] = None
    escrow_events: List[Any] = Field(default_factory=list)


class MessageUser(BaseModel):
    """User information in a message"""
    id: int
    name: str
    profile_image: Optional[str] = None
    profile: Optional[str] = None  # For system messages
    provider: Optional[MessageProviderInfo] = None


class MessageFileItem(BaseModel):
    """Individual file in a message"""
    id: int
    type: str
    file: str
    file_name: str
    extension: str
    size: int


class MessageFiles(BaseModel):
    """Files attached to a message"""
    images: List[MessageFileItem] = Field(default_factory=list)
    videos: List[MessageFileItem] = Field(default_factory=list)
    files: List[MessageFileItem] = Field(default_factory=list)


class MessageItem(BaseModel):
    """Individual message item from the API response"""
    id: int
    user: MessageUser
    type: str
    own_type: str
    message: str
    system: Optional[Dict[str, Any]] = None
    file: Optional[Dict[str, Any]] = None
    files: Optional[MessageFiles] = None
    is_receiver_read: bool
    created_at: str
    nonce: Optional[str] = None
    calendar: Optional[Dict[str, Any]] = None
    auto_message: Optional[Dict[str, Any]] = None
    call_data: Optional[Dict[str, Any]] = None


class MessageListResponse(BaseModel):
    """Response from the chat messages API"""
    prev: Optional[int] = None
    next: Optional[int] = None
    results: List[MessageItem]


# ===== Scraping Run Metadata =====

class ErrorInfo(BaseModel):
    """Error information during scraping"""
    error: str
    context: str
    timestamp: str


class ScrapingRunMetadata(BaseModel):
    """Metadata for a scraping run"""
    run_id: str
    run_type: str  # "chat_list" or "chat_messages"
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "in_progress", "completed", "failed", "partial"

    # Counts
    total_items_found: int = 0
    total_items_processed: int = 0
    total_items_failed: int = 0
    total_duplicates_filtered: int = 0

    # Performance
    duration_seconds: Optional[float] = None
    items_per_second: Optional[float] = None

    # Errors
    errors: List[ErrorInfo] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)

    # Output files
    output_files: List[str] = Field(default_factory=list)


class HumanizationStats(BaseModel):
    """Statistics for humanization behavior"""
    reading_pauses: int = 0  # Times we paused to "read"
    scroll_ups: int = 0  # Times we scrolled up slightly
    mouse_movements: int = 0  # Times we moved mouse randomly
    session_breaks: int = 0  # Times we took a break (>10s pause)
    total_wait_time_seconds: float = 0  # Total time spent waiting


class EfficiencyMetrics(BaseModel):
    """Efficiency metrics for scraping"""
    chats_per_api_call: Optional[float] = None  # Average new chats per API call
    chats_per_scroll: Optional[float] = None  # Average new chats per scroll
    api_calls_per_minute: Optional[float] = None
    scrolls_per_minute: Optional[float] = None


class ChatListScrapingRunMetadata(ScrapingRunMetadata):
    """Specific metadata for chat list scraping"""
    scroll_iterations: int = 0
    api_calls_intercepted: int = 0
    oldest_chat_date: Optional[str] = None
    newest_chat_date: Optional[str] = None
    unique_services: List[str] = Field(default_factory=list)

    # Enhanced metrics
    first_api_call_at: Optional[datetime] = None
    last_api_call_at: Optional[datetime] = None
    humanization_stats: HumanizationStats = Field(default_factory=HumanizationStats)
    efficiency_metrics: EfficiencyMetrics = Field(default_factory=EfficiencyMetrics)

    # Safety metrics
    rate_limit_hits: int = 0  # Times we hit rate limiting
    backoff_events: int = 0  # Times we applied exponential backoff
    viewport_changes: int = 0  # Times we changed viewport size


class ChatScrapingStatus(BaseModel):
    """Status of scraping messages for a single chat"""
    chat_id: int
    status: str  # "success", "failed", "skipped", "deleted"
    message_count: int = 0
    api_calls: int = 0
    scroll_iterations: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


class MessageScrapingRunMetadata(ScrapingRunMetadata):
    """Specific metadata for message scraping runs"""
    chats_attempted: int = 0
    chats_succeeded: int = 0
    chats_failed: int = 0
    chats_skipped: int = 0
    total_messages_scraped: int = 0

    # Chat statuses
    chat_statuses: List[ChatScrapingStatus] = Field(default_factory=list)

    # Humanization
    humanization_stats: HumanizationStats = Field(default_factory=HumanizationStats)

    # Date filter used
    date_filter: str = "all"  # "all" or "30days"
    chat_limit: Optional[int] = None  # Batch limit if used
