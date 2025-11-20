"""Data quality validation and reporting."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter
from pydantic import BaseModel, Field
import statistics


class FieldCompleteness(BaseModel):
    """Completeness stats for a field"""
    field_name: str
    total_records: int
    non_null_count: int
    null_count: int
    completeness_percent: float


class AnomalyReport(BaseModel):
    """Anomaly detection report"""
    anomaly_type: str
    severity: str  # "warning", "error", "info"
    count: int
    details: str
    sample_ids: List[int] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    issue_type: str
    severity: str
    chat_id: int
    field: str
    message: str


class DataQualityReport(BaseModel):
    """Comprehensive data quality report"""
    generated_at: datetime
    total_records: int

    # Completeness
    completeness_summary: List[FieldCompleteness] = Field(default_factory=list)
    overall_completeness_percent: float = 0.0

    # Validity
    validation_issues: List[ValidationIssue] = Field(default_factory=list)
    valid_records_count: int = 0
    invalid_records_count: int = 0

    # Consistency
    duplicate_ids: List[int] = Field(default_factory=list)
    timeline_inconsistencies: List[int] = Field(default_factory=list)

    # Anomalies
    anomalies: List[AnomalyReport] = Field(default_factory=list)

    # Coverage
    date_range: Dict[str, Optional[str]] = Field(default_factory=dict)
    date_gaps: List[Dict[str, str]] = Field(default_factory=list)
    service_distribution: Dict[str, int] = Field(default_factory=dict)

    # Summary Statistics
    statistics: Dict[str, Any] = Field(default_factory=dict)

    # Overall Score
    quality_score: float = 0.0
    quality_grade: str = "Unknown"


class DataQualityAnalyzer:
    """Analyzes chat data for quality issues"""

    def __init__(self, chats: List[Dict[str, Any]]):
        self.chats = chats
        self.report = DataQualityReport(
            generated_at=datetime.now(),
            total_records=len(chats)
        )

    def analyze(self) -> DataQualityReport:
        """Run all quality checks and generate report"""
        if not self.chats:
            self.report.quality_grade = "N/A - No Data"
            return self.report

        # Run all checks
        self._check_completeness()
        self._check_validity()
        self._check_consistency()
        self._detect_anomalies()
        self._analyze_coverage()
        self._calculate_statistics()

        # Calculate overall quality score
        self._calculate_quality_score()

        return self.report

    def _check_completeness(self):
        """Check field completeness"""
        if not self.chats:
            return

        # Define critical fields to check
        fields_to_check = [
            'id', 'created_at', 'updated_at', 'last_message',
            'service.title', 'user.id', 'user.name', 'quote.price'
        ]

        total = len(self.chats)
        completeness_data = []

        for field_path in fields_to_check:
            non_null = 0
            for chat in self.chats:
                value = self._get_nested_field(chat, field_path)
                if value is not None and value != "":
                    non_null += 1

            null_count = total - non_null
            completeness_pct = (non_null / total * 100) if total > 0 else 0

            completeness_data.append(FieldCompleteness(
                field_name=field_path,
                total_records=total,
                non_null_count=non_null,
                null_count=null_count,
                completeness_percent=completeness_pct
            ))

        self.report.completeness_summary = completeness_data

        # Calculate overall completeness
        if completeness_data:
            avg_completeness = sum(c.completeness_percent for c in completeness_data) / len(completeness_data)
            self.report.overall_completeness_percent = avg_completeness

    def _check_validity(self):
        """Check data validity"""
        valid_count = 0

        for chat in self.chats:
            chat_valid = True
            chat_id = chat.get('id', 0)

            # Check date formats
            for date_field in ['created_at', 'updated_at']:
                date_str = chat.get(date_field)
                if date_str:
                    try:
                        parsed = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        # Check for future dates
                        if parsed > datetime.now():
                            self.report.validation_issues.append(ValidationIssue(
                                issue_type="future_date",
                                severity="warning",
                                chat_id=chat_id,
                                field=date_field,
                                message=f"Date is in the future: {date_str}"
                            ))
                            chat_valid = False
                    except:
                        self.report.validation_issues.append(ValidationIssue(
                            issue_type="invalid_date",
                            severity="error",
                            chat_id=chat_id,
                            field=date_field,
                            message=f"Invalid date format: {date_str}"
                        ))
                        chat_valid = False

            # Check numeric ranges
            quote = chat.get('quote', {})
            price = quote.get('price')
            if price is not None and price < 0:
                self.report.validation_issues.append(ValidationIssue(
                    issue_type="invalid_range",
                    severity="error",
                    chat_id=chat_id,
                    field="quote.price",
                    message=f"Negative price: {price}"
                ))
                chat_valid = False

            # Check message counts
            new_msg_count = chat.get('new_message_count', 0)
            provider_msg_count = chat.get('provider_message_count', 0)
            if new_msg_count < 0 or provider_msg_count < 0:
                self.report.validation_issues.append(ValidationIssue(
                    issue_type="invalid_range",
                    severity="error",
                    chat_id=chat_id,
                    field="message_count",
                    message=f"Negative message count"
                ))
                chat_valid = False

            if chat_valid:
                valid_count += 1

        self.report.valid_records_count = valid_count
        self.report.invalid_records_count = len(self.chats) - valid_count

    def _check_consistency(self):
        """Check data consistency"""
        seen_ids = set()

        for chat in self.chats:
            chat_id = chat.get('id')

            # Check for duplicate IDs
            if chat_id in seen_ids:
                self.report.duplicate_ids.append(chat_id)
            else:
                seen_ids.add(chat_id)

            # Check timeline consistency (created_at <= updated_at)
            created_str = chat.get('created_at')
            updated_str = chat.get('updated_at')

            if created_str and updated_str:
                try:
                    created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))

                    if created > updated:
                        self.report.timeline_inconsistencies.append(chat_id)
                except:
                    pass  # Already caught in validity checks

    def _detect_anomalies(self):
        """Detect anomalies in data"""
        # Collect numeric fields for outlier detection
        prices = []
        new_msg_counts = []
        provider_msg_counts = []
        user_ids = []

        for chat in self.chats:
            quote = chat.get('quote', {})
            price = quote.get('price')
            if price is not None and price >= 0:
                prices.append((chat.get('id'), price))

            new_msg = chat.get('new_message_count', 0)
            new_msg_counts.append((chat.get('id'), new_msg))

            provider_msg = chat.get('provider_message_count', 0)
            provider_msg_counts.append((chat.get('id'), provider_msg))

            user = chat.get('user', {})
            user_ids.append(user.get('id'))

        # Detect price outliers
        if len(prices) > 10:
            price_values = [p[1] for p in prices]
            self._detect_outliers(prices, "price", "quote.price")

        # Detect excessive new messages
        excessive_new_msgs = [(id, count) for id, count in new_msg_counts if count > 50]
        if excessive_new_msgs:
            self.report.anomalies.append(AnomalyReport(
                anomaly_type="excessive_unread_messages",
                severity="warning",
                count=len(excessive_new_msgs),
                details=f"{len(excessive_new_msgs)} chats with >50 unread messages",
                sample_ids=[id for id, _ in excessive_new_msgs[:5]]
            ))

        # Detect suspicious user patterns (same user multiple chats)
        user_counter = Counter(user_ids)
        frequent_users = [(user_id, count) for user_id, count in user_counter.items() if count > 10]
        if frequent_users:
            self.report.anomalies.append(AnomalyReport(
                anomaly_type="frequent_user",
                severity="info",
                count=len(frequent_users),
                details=f"{len(frequent_users)} users with >10 chats",
                sample_ids=[]  # User IDs, not chat IDs
            ))

        # Detect banned/dormant/left users
        banned_count = sum(1 for chat in self.chats if chat.get('user', {}).get('is_banned'))
        dormant_count = sum(1 for chat in self.chats if chat.get('user', {}).get('is_dormant'))
        left_count = sum(1 for chat in self.chats if chat.get('user', {}).get('is_leaved'))

        if banned_count > 0:
            self.report.anomalies.append(AnomalyReport(
                anomaly_type="banned_users",
                severity="warning",
                count=banned_count,
                details=f"{banned_count} chats with banned users",
                sample_ids=[]
            ))

        if dormant_count > 0:
            self.report.anomalies.append(AnomalyReport(
                anomaly_type="dormant_users",
                severity="info",
                count=dormant_count,
                details=f"{dormant_count} chats with dormant users",
                sample_ids=[]
            ))

    def _detect_outliers(self, data_pairs: List[tuple], field_name: str, field_path: str):
        """Detect outliers using IQR method"""
        if len(data_pairs) < 4:
            return

        values = [v for _, v in data_pairs]
        values.sort()

        q1 = statistics.quantiles(values, n=4)[0]
        q3 = statistics.quantiles(values, n=4)[2]
        iqr = q3 - q1

        lower_bound = q1 - 3 * iqr
        upper_bound = q3 + 3 * iqr

        outliers = [(id, v) for id, v in data_pairs if v < lower_bound or v > upper_bound]

        if outliers:
            self.report.anomalies.append(AnomalyReport(
                anomaly_type=f"outlier_{field_name}",
                severity="warning",
                count=len(outliers),
                details=f"{len(outliers)} outliers in {field_path} (IQR method)",
                sample_ids=[id for id, _ in outliers[:5]]
            ))

    def _analyze_coverage(self):
        """Analyze data coverage"""
        if not self.chats:
            return

        # Date range (using updated_at for activity range)
        dates = []
        for chat in self.chats:
            updated_str = chat.get('updated_at')
            if updated_str:
                try:
                    dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                    dates.append(dt)
                except:
                    pass

        if dates:
            dates.sort()
            self.report.date_range = {
                "oldest": dates[0].isoformat(),
                "newest": dates[-1].isoformat(),
                "span_days": (dates[-1] - dates[0]).days
            }

            # Detect date gaps (>7 days between consecutive chats)
            for i in range(len(dates) - 1):
                gap_days = (dates[i + 1] - dates[i]).days
                if gap_days > 7:
                    self.report.date_gaps.append({
                        "start": dates[i].isoformat(),
                        "end": dates[i + 1].isoformat(),
                        "gap_days": gap_days
                    })

        # Service distribution
        service_counter = Counter()
        for chat in self.chats:
            service = chat.get('service', {})
            title = service.get('title', 'Unknown')
            service_counter[title] += 1

        self.report.service_distribution = dict(service_counter.most_common(20))

    def _calculate_statistics(self):
        """Calculate summary statistics"""
        if not self.chats:
            return

        total = len(self.chats)

        # Hiring statistics
        hired_count = sum(1 for chat in self.chats if chat.get('quote', {}).get('is_hired'))
        hiring_rate = (hired_count / total * 100) if total > 0 else 0

        # Price statistics
        prices = [chat.get('quote', {}).get('price', 0) for chat in self.chats
                  if chat.get('quote', {}).get('price') is not None]

        price_stats = {}
        if prices:
            price_stats = {
                "min": min(prices),
                "max": max(prices),
                "mean": statistics.mean(prices),
                "median": statistics.median(prices)
            }

        # Message statistics
        new_msgs = [chat.get('new_message_count', 0) for chat in self.chats]
        provider_msgs = [chat.get('provider_message_count', 0) for chat in self.chats]

        # User statistics
        active_users = sum(1 for chat in self.chats if chat.get('user', {}).get('is_active'))
        certified_users = sum(1 for chat in self.chats if chat.get('user', {}).get('is_certify_name'))

        # Unlock statistics
        unlocked = sum(1 for chat in self.chats if chat.get('unlock'))
        unlock_customer = sum(1 for chat in self.chats if chat.get('unlock_customer'))

        # Favorite statistics
        favorites = sum(1 for chat in self.chats if chat.get('is_favorite'))

        self.report.statistics = {
            "total_chats": total,
            "unique_services": len(self.report.service_distribution),
            "hiring": {
                "hired_count": hired_count,
                "hiring_rate_percent": round(hiring_rate, 2)
            },
            "price": price_stats,
            "messages": {
                "avg_new_messages": round(statistics.mean(new_msgs), 2) if new_msgs else 0,
                "avg_provider_messages": round(statistics.mean(provider_msgs), 2) if provider_msgs else 0,
                "total_unread": sum(new_msgs)
            },
            "users": {
                "active_count": active_users,
                "active_percent": round(active_users / total * 100, 2) if total > 0 else 0,
                "certified_count": certified_users,
                "certified_percent": round(certified_users / total * 100, 2) if total > 0 else 0
            },
            "unlock": {
                "unlocked_count": unlocked,
                "unlock_customer_count": unlock_customer
            },
            "favorites_count": favorites
        }

    def _calculate_quality_score(self):
        """Calculate overall quality score (0-100)"""
        scores = []

        # Completeness score (40% weight)
        completeness_score = self.report.overall_completeness_percent
        scores.append(completeness_score * 0.4)

        # Validity score (30% weight)
        if self.report.total_records > 0:
            validity_percent = (self.report.valid_records_count / self.report.total_records) * 100
            scores.append(validity_percent * 0.3)

        # Consistency score (20% weight)
        duplicate_penalty = len(self.report.duplicate_ids) * 2
        timeline_penalty = len(self.report.timeline_inconsistencies) * 1
        consistency_score = max(0, 100 - duplicate_penalty - timeline_penalty)
        scores.append(consistency_score * 0.2)

        # Anomaly score (10% weight)
        critical_anomalies = sum(1 for a in self.report.anomalies if a.severity == "error")
        warning_anomalies = sum(1 for a in self.report.anomalies if a.severity == "warning")
        anomaly_penalty = critical_anomalies * 10 + warning_anomalies * 5
        anomaly_score = max(0, 100 - anomaly_penalty)
        scores.append(anomaly_score * 0.1)

        # Calculate final score
        final_score = sum(scores)
        self.report.quality_score = round(final_score, 2)

        # Assign grade
        if final_score >= 95:
            self.report.quality_grade = "A+ (Excellent)"
        elif final_score >= 90:
            self.report.quality_grade = "A (Very Good)"
        elif final_score >= 85:
            self.report.quality_grade = "B+ (Good)"
        elif final_score >= 80:
            self.report.quality_grade = "B (Acceptable)"
        elif final_score >= 70:
            self.report.quality_grade = "C (Fair)"
        elif final_score >= 60:
            self.report.quality_grade = "D (Poor)"
        else:
            self.report.quality_grade = "F (Failed)"

    def _get_nested_field(self, obj: Dict, field_path: str) -> Any:
        """Get nested field value using dot notation"""
        parts = field_path.split('.')
        current = obj

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

            if current is None:
                return None

        return current


def generate_quality_report(chats: List[Dict[str, Any]]) -> DataQualityReport:
    """Generate a comprehensive data quality report"""
    analyzer = DataQualityAnalyzer(chats)
    return analyzer.analyze()
