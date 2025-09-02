#!/usr/bin/env python3
"""
Flink State Management Examples - Building Block Application

This module demonstrates sophisticated state management patterns with Apache Flink:
- Keyed state management (ValueState, ListState, MapState)
- Operator state management and checkpointing
- State TTL and cleanup strategies
- Complex event processing with state
- State evolution and migration
- Custom state backends configuration

Usage:
    bazel run //flink/python:state_management -- --state-types keyed,operator,complex

Examples:
    # Basic state management
    bazel run //flink/python:state_management
    
    # All state types with custom TTL
    bazel run //flink/python:state_management -- --state-types all --state-ttl 3600
    
    # Complex event processing
    bazel run //flink/python:state_management -- --enable-cep --duration 300
"""

import sys
import time
import json
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flink_common import (
    FlinkConfig,
    create_flink_environment,
    create_table_environment,
    generate_sample_streaming_data,
    create_kafka_source,
    create_kafka_sink,
    monitor_job_progress,
    parse_common_args,
    handle_errors,
    cleanup_environment,
    metrics_tracker,
)

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.common import Types, WatermarkStrategy, Duration, Time
    from pyflink.datastream.functions import (
        KeyedProcessFunction,
        ProcessFunction,
        MapFunction,
        BroadcastProcessFunction,
        CoProcessFunction,
    )
    from pyflink.common.state import (
        ValueStateDescriptor,
        ListStateDescriptor,
        MapStateDescriptor,
        BroadcastStateDescriptor,
        StateTtlConfig,
        StateTtlConfigBuilder,
    )
    from pyflink.common.time import Time as FlinkTime
    from pyflink.datastream.state import RuntimeContext
    from pyflink.common.typeinfo import TypeInformation
except ImportError:
    print("ERROR: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)


class UserProfile:
    """User profile data structure for state management."""

    def __init__(
        self,
        user_id: str,
        username: str = "",
        email: str = "",
        tier: str = "BRONZE",
        total_spent: float = 0.0,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.tier = tier
        self.total_spent = total_spent
        self.last_activity = datetime.now()
        self.session_count = 0
        self.purchase_history = []
        self.preferences = {}

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "tier": self.tier,
            "total_spent": self.total_spent,
            "last_activity": self.last_activity.isoformat(),
            "session_count": self.session_count,
            "purchase_history": self.purchase_history,
            "preferences": self.preferences,
        }

    @classmethod
    def from_dict(cls, data: dict):
        profile = cls(
            data["user_id"],
            data.get("username", ""),
            data.get("email", ""),
            data.get("tier", "BRONZE"),
            data.get("total_spent", 0.0),
        )
        profile.last_activity = datetime.fromisoformat(
            data.get("last_activity", datetime.now().isoformat())
        )
        profile.session_count = data.get("session_count", 0)
        profile.purchase_history = data.get("purchase_history", [])
        profile.preferences = data.get("preferences", {})
        return profile


class EventData:
    """Enhanced event data with state management fields."""

    def __init__(self, json_str: str):
        try:
            data = json.loads(json_str)
            self.event_id = data.get("event_id", "")
            self.user_id = data.get("user_id", "")
            self.session_id = data.get("session_id", "")
            self.product_id = data.get("product_id", "")
            self.category = data.get("category", "")
            self.action = data.get("action", "")
            self.price = float(data.get("price", 0))
            self.quantity = int(data.get("quantity", 0))
            self.timestamp = data.get("timestamp", datetime.now().isoformat())
            self.metadata = data.get("metadata", {})
            self.total_amount = self.price * self.quantity

            # Parse event time
            try:
                self.event_time = datetime.fromisoformat(
                    self.timestamp.replace("Z", "+00:00")
                )
            except:
                self.event_time = datetime.now()

        except Exception:
            self._set_defaults()

    def _set_defaults(self):
        """Set default values for malformed data."""
        self.event_id = "invalid"
        self.user_id = "unknown"
        self.session_id = "unknown"
        self.product_id = "unknown"
        self.category = "unknown"
        self.action = "unknown"
        self.price = 0.0
        self.quantity = 0
        self.timestamp = datetime.now().isoformat()
        self.metadata = {}
        self.total_amount = 0.0
        self.event_time = datetime.now()

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "product_id": self.product_id,
            "category": self.category,
            "action": self.action,
            "price": self.price,
            "quantity": self.quantity,
            "total_amount": self.total_amount,
            "timestamp": self.timestamp,
            "event_time_ms": int(self.event_time.timestamp() * 1000),
            "metadata": self.metadata,
        }


class UserProfileManager(KeyedProcessFunction):
    """Manages user profiles with ValueState."""

    def __init__(self, state_ttl_hours: int = 24):
        self.state_ttl_hours = state_ttl_hours
        self.profile_state = None
        self.last_login_state = None
        self.tier_change_timer_state = None

    def open(self, runtime_context: RuntimeContext):
        """Initialize state descriptors with TTL configuration."""
        # Configure TTL for state cleanup
        ttl_config = (
            StateTtlConfigBuilder.new_builder(Time.hours(self.state_ttl_hours))
            .set_update_type(StateTtlConfig.UpdateType.ON_READ_AND_WRITE)
            .set_state_visibility(StateTtlConfig.StateVisibility.NEVER_RETURN_EXPIRED)
            .cleanup_incrementally(1000, True)  # Cleanup during checkpointing
            .build()
        )

        # User profile state
        profile_descriptor = ValueStateDescriptor(
            "user_profile", TypeInformation.of(Types.PICKLED_BYTE_ARRAY())
        )
        profile_descriptor.enable_time_to_live(ttl_config)
        self.profile_state = runtime_context.get_state(profile_descriptor)

        # Last login timestamp
        login_descriptor = ValueStateDescriptor(
            "last_login", TypeInformation.of(Types.LONG())
        )
        login_descriptor.enable_time_to_live(ttl_config)
        self.last_login_state = runtime_context.get_state(login_descriptor)

        # Timer for tier upgrades
        timer_descriptor = ValueStateDescriptor(
            "tier_timer", TypeInformation.of(Types.LONG())
        )
        self.tier_change_timer_state = runtime_context.get_state(timer_descriptor)

    def process_element(self, value, ctx, out):
        """Process events and update user profile state."""
        event = value
        current_time = ctx.timestamp()

        # Get or create user profile
        profile_data = self.profile_state.value()
        if profile_data is None:
            profile = UserProfile(event["user_id"])
        else:
            profile = UserProfile.from_dict(json.loads(profile_data))

        # Update profile based on event
        profile.last_activity = datetime.fromtimestamp(current_time / 1000)

        if event["action"] == "login":
            profile.session_count += 1
            self.last_login_state.update(current_time)

        elif event["action"] == "purchase":
            profile.total_spent += event["total_amount"]
            profile.purchase_history.append(
                {
                    "product_id": event["product_id"],
                    "category": event["category"],
                    "amount": event["total_amount"],
                    "timestamp": event["timestamp"],
                }
            )

            # Keep only last 10 purchases in state
            if len(profile.purchase_history) > 10:
                profile.purchase_history = profile.purchase_history[-10:]

            # Check for tier upgrade
            self._check_tier_upgrade(profile, ctx, current_time)

        elif event["action"] == "view":
            # Update category preferences
            category = event["category"]
            profile.preferences[category] = profile.preferences.get(category, 0) + 1

        # Update state
        self.profile_state.update(json.dumps(profile.to_dict()))

        # Emit enriched event
        enriched_event = {
            **event,
            "user_profile": profile.to_dict(),
            "processing_time": current_time,
        }

        out.collect(enriched_event)
        metrics_tracker.increment("profiles_updated")

    def _check_tier_upgrade(self, profile: UserProfile, ctx, current_time: int):
        """Check if user qualifies for tier upgrade."""
        old_tier = profile.tier

        if profile.total_spent >= 5000 and profile.tier != "PLATINUM":
            profile.tier = "PLATINUM"
        elif profile.total_spent >= 2000 and profile.tier not in ["GOLD", "PLATINUM"]:
            profile.tier = "GOLD"
        elif profile.total_spent >= 500 and profile.tier not in [
            "SILVER",
            "GOLD",
            "PLATINUM",
        ]:
            profile.tier = "SILVER"

        # If tier changed, set timer for tier benefits activation
        if old_tier != profile.tier:
            tier_activation_time = current_time + (24 * 60 * 60 * 1000)  # 24 hours
            self.tier_change_timer_state.update(tier_activation_time)
            ctx.timer_service().register_event_time_timer(tier_activation_time)

            metrics_tracker.increment("tier_upgrades")

    def on_timer(self, timestamp: int, ctx, out):
        """Handle tier activation timer."""
        profile_data = self.profile_state.value()
        if profile_data:
            profile = UserProfile.from_dict(json.loads(profile_data))

            # Emit tier activation event
            tier_event = {
                "event_type": "TIER_ACTIVATED",
                "user_id": profile.user_id,
                "new_tier": profile.tier,
                "total_spent": profile.total_spent,
                "activation_time": timestamp,
                "benefits": self._get_tier_benefits(profile.tier),
            }

            out.collect(tier_event)

            # Clear timer state
            self.tier_change_timer_state.clear()

    def _get_tier_benefits(self, tier: str) -> List[str]:
        """Get benefits for user tier."""
        benefits = {
            "BRONZE": ["Basic support"],
            "SILVER": ["Basic support", "5% discount"],
            "GOLD": ["Priority support", "10% discount", "Free shipping"],
            "PLATINUM": [
                "VIP support",
                "15% discount",
                "Free shipping",
                "Early access",
            ],
        }
        return benefits.get(tier, [])


class SessionAnalyzer(KeyedProcessFunction):
    """Analyzes user sessions using ListState."""

    def __init__(self, session_timeout_minutes: int = 30):
        self.session_timeout_ms = session_timeout_minutes * 60 * 1000
        self.session_events_state = None
        self.session_start_state = None
        self.session_timer_state = None

    def open(self, runtime_context: RuntimeContext):
        """Initialize session state descriptors."""
        # List of events in current session
        events_descriptor = ListStateDescriptor(
            "session_events", TypeInformation.of(Types.PICKLED_BYTE_ARRAY())
        )
        self.session_events_state = runtime_context.get_list_state(events_descriptor)

        # Session start time
        start_descriptor = ValueStateDescriptor(
            "session_start", TypeInformation.of(Types.LONG())
        )
        self.session_start_state = runtime_context.get_state(start_descriptor)

        # Session timeout timer
        timer_descriptor = ValueStateDescriptor(
            "session_timer", TypeInformation.of(Types.LONG())
        )
        self.session_timer_state = runtime_context.get_state(timer_descriptor)

    def process_element(self, value, ctx, out):
        """Process events and manage session state."""
        event = value
        current_time = ctx.timestamp()

        # Get current session state
        session_start = self.session_start_state.value()
        current_events = list(self.session_events_state.get())

        # Start new session if needed
        if session_start is None:
            session_start = current_time
            self.session_start_state.update(session_start)

        # Add event to session
        self.session_events_state.add(json.dumps(event))
        current_events.append(event)

        # Update session timeout timer
        timeout_time = current_time + self.session_timeout_ms
        self.session_timer_state.update(timeout_time)
        ctx.timer_service().register_event_time_timer(timeout_time)

        # Emit real-time session metrics
        session_metrics = self._calculate_session_metrics(
            current_events, session_start, current_time
        )
        session_metrics["user_id"] = event["user_id"]
        session_metrics["is_active"] = True

        out.collect(session_metrics)
        metrics_tracker.increment("session_updates")

    def on_timer(self, timestamp: int, ctx, out):
        """Handle session timeout."""
        session_start = self.session_start_state.value()
        current_events = list(self.session_events_state.get())

        if session_start and current_events:
            # Calculate final session metrics
            final_metrics = self._calculate_session_metrics(
                current_events, session_start, timestamp
            )
            final_metrics["user_id"] = current_events[0]["user_id"]
            final_metrics["is_active"] = False
            final_metrics["session_ended"] = True

            out.collect(final_metrics)
            metrics_tracker.increment("sessions_completed")

        # Clear session state
        self.session_events_state.clear()
        self.session_start_state.clear()
        self.session_timer_state.clear()

    def _calculate_session_metrics(
        self, events: List[dict], session_start: int, current_time: int
    ) -> dict:
        """Calculate comprehensive session metrics."""
        if not events:
            return {}

        session_duration_ms = current_time - session_start
        event_count = len(events)

        # Calculate various metrics
        unique_products = len(set(e["product_id"] for e in events))
        unique_categories = len(set(e["category"] for e in events))
        total_spent = sum(
            e["total_amount"] for e in events if e["action"] == "purchase"
        )
        view_count = len([e for e in events if e["action"] == "view"])
        purchase_count = len([e for e in events if e["action"] == "purchase"])

        # Action sequence analysis
        actions = [e["action"] for e in events]
        action_sequence = " -> ".join(actions)

        # Conversion metrics
        conversion_rate = purchase_count / max(view_count, 1) if view_count > 0 else 0

        # Engagement scoring
        engagement_score = (
            view_count * 1
            + len([e for e in events if e["action"] == "add_to_cart"]) * 3
            + purchase_count * 5
            + unique_categories * 2
        )

        return {
            "session_duration_ms": session_duration_ms,
            "session_duration_minutes": session_duration_ms / (1000 * 60),
            "event_count": event_count,
            "unique_products": unique_products,
            "unique_categories": unique_categories,
            "total_spent": total_spent,
            "view_count": view_count,
            "purchase_count": purchase_count,
            "conversion_rate": conversion_rate,
            "engagement_score": engagement_score,
            "action_sequence": action_sequence,
            "avg_time_between_events_ms": (
                session_duration_ms / max(event_count - 1, 1) if event_count > 1 else 0
            ),
        }


class ProductPopularityTracker(KeyedProcessFunction):
    """Tracks product popularity using MapState."""

    def __init__(self, window_hours: int = 1):
        self.window_duration_ms = window_hours * 60 * 60 * 1000
        self.hourly_metrics_state = None
        self.window_timer_state = None

    def open(self, runtime_context: RuntimeContext):
        """Initialize product popularity state descriptors."""
        # Map of hour -> metrics
        metrics_descriptor = MapStateDescriptor(
            "hourly_metrics",
            TypeInformation.of(Types.LONG()),  # hour as key
            TypeInformation.of(Types.PICKLED_BYTE_ARRAY()),  # metrics as value
        )
        self.hourly_metrics_state = runtime_context.get_map_state(metrics_descriptor)

        # Timer for window cleanup
        timer_descriptor = ValueStateDescriptor(
            "window_timer", TypeInformation.of(Types.LONG())
        )
        self.window_timer_state = runtime_context.get_state(timer_descriptor)

    def process_element(self, value, ctx, out):
        """Process events and update product popularity metrics."""
        event = value
        current_time = ctx.timestamp()
        current_hour = current_time // (60 * 60 * 1000)  # Convert to hour

        # Get or create metrics for current hour
        metrics_data = self.hourly_metrics_state.get(current_hour)
        if metrics_data is None:
            metrics = {
                "view_count": 0,
                "purchase_count": 0,
                "total_revenue": 0.0,
                "unique_users": set(),
                "first_seen": current_time,
                "last_seen": current_time,
            }
        else:
            metrics = json.loads(metrics_data)
            metrics["unique_users"] = set(metrics["unique_users"])

        # Update metrics based on event
        if event["action"] == "view":
            metrics["view_count"] += 1
        elif event["action"] == "purchase":
            metrics["purchase_count"] += 1
            metrics["total_revenue"] += event["total_amount"]

        metrics["unique_users"].add(event["user_id"])
        metrics["last_seen"] = current_time

        # Convert set back to list for JSON serialization
        metrics_to_store = dict(metrics)
        metrics_to_store["unique_users"] = list(metrics["unique_users"])

        # Update state
        self.hourly_metrics_state.put(current_hour, json.dumps(metrics_to_store))

        # Set timer for cleanup (keep last 24 hours)
        cleanup_time = current_time + (24 * 60 * 60 * 1000)
        self.window_timer_state.update(cleanup_time)
        ctx.timer_service().register_event_time_timer(cleanup_time)

        # Calculate and emit current popularity metrics
        popularity_metrics = self._calculate_popularity_metrics(current_hour)
        popularity_metrics["product_id"] = event["product_id"]
        popularity_metrics["category"] = event["category"]
        popularity_metrics["current_hour"] = current_hour

        out.collect(popularity_metrics)
        metrics_tracker.increment("popularity_updates")

    def on_timer(self, timestamp: int, ctx, out):
        """Clean up old hourly metrics."""
        current_hour = timestamp // (60 * 60 * 1000)
        cutoff_hour = current_hour - 24  # Keep last 24 hours

        # Remove old entries
        hours_to_remove = []
        for hour in self.hourly_metrics_state.keys():
            if hour < cutoff_hour:
                hours_to_remove.append(hour)

        for hour in hours_to_remove:
            self.hourly_metrics_state.remove(hour)

        metrics_tracker.increment("state_cleanups")

    def _calculate_popularity_metrics(self, current_hour: int) -> dict:
        """Calculate comprehensive popularity metrics."""
        total_views = 0
        total_purchases = 0
        total_revenue = 0.0
        all_users = set()
        hours_with_activity = 0

        # Aggregate metrics across all hours
        for hour, metrics_data in self.hourly_metrics_state.items():
            if metrics_data:
                metrics = json.loads(metrics_data)
                total_views += metrics["view_count"]
                total_purchases += metrics["purchase_count"]
                total_revenue += metrics["total_revenue"]
                all_users.update(metrics["unique_users"])
                if metrics["view_count"] > 0 or metrics["purchase_count"] > 0:
                    hours_with_activity += 1

        # Calculate derived metrics
        conversion_rate = total_purchases / max(total_views, 1)
        revenue_per_view = total_revenue / max(total_views, 1)
        revenue_per_user = total_revenue / max(len(all_users), 1)

        # Popularity score (weighted combination of metrics)
        popularity_score = (
            total_views * 1
            + total_purchases * 5
            + len(all_users) * 3
            + hours_with_activity * 2
        )

        return {
            "total_views": total_views,
            "total_purchases": total_purchases,
            "total_revenue": total_revenue,
            "unique_users": len(all_users),
            "conversion_rate": conversion_rate,
            "revenue_per_view": revenue_per_view,
            "revenue_per_user": revenue_per_user,
            "hours_with_activity": hours_with_activity,
            "popularity_score": popularity_score,
        }


class FeatureStoreProcessor(ProcessFunction):
    """Complex event processing for real-time feature store updates."""

    def __init__(self):
        self.user_features = {}
        self.product_features = {}
        self.session_features = {}

    def process_element(self, value, ctx, out):
        """Process events and generate real-time features."""
        event = value
        current_time = ctx.timestamp()

        # Generate user features
        user_features = self._generate_user_features(event, current_time)

        # Generate product features
        product_features = self._generate_product_features(event, current_time)

        # Generate session features
        session_features = self._generate_session_features(event, current_time)

        # Combine all features
        feature_vector = {
            "user_id": event["user_id"],
            "product_id": event["product_id"],
            "session_id": event["session_id"],
            "timestamp": current_time,
            "user_features": user_features,
            "product_features": product_features,
            "session_features": session_features,
            "event_features": {
                "action": event["action"],
                "category": event["category"],
                "price": event["price"],
                "hour_of_day": datetime.fromtimestamp(current_time / 1000).hour,
                "day_of_week": datetime.fromtimestamp(current_time / 1000).weekday(),
            },
        }

        out.collect(feature_vector)
        metrics_tracker.increment("features_generated")

    def _generate_user_features(self, event: dict, current_time: int) -> dict:
        """Generate user-specific features."""
        user_id = event["user_id"]

        # Update user feature state (in real implementation, this would use proper state)
        if user_id not in self.user_features:
            self.user_features[user_id] = {
                "total_events": 0,
                "total_spent": 0.0,
                "unique_categories": set(),
                "last_activity": current_time,
                "session_count": 0,
            }

        user_state = self.user_features[user_id]
        user_state["total_events"] += 1
        user_state["unique_categories"].add(event["category"])

        if event["action"] == "purchase":
            user_state["total_spent"] += event["total_amount"]

        # Calculate time-based features
        time_since_last_activity = current_time - user_state["last_activity"]
        user_state["last_activity"] = current_time

        return {
            "total_events": user_state["total_events"],
            "total_spent": user_state["total_spent"],
            "unique_categories_count": len(user_state["unique_categories"]),
            "avg_spending": user_state["total_spent"]
            / max(user_state["total_events"], 1),
            "time_since_last_activity_ms": time_since_last_activity,
            "is_frequent_user": user_state["total_events"] > 10,
            "is_high_value_user": user_state["total_spent"] > 1000,
        }

    def _generate_product_features(self, event: dict, current_time: int) -> dict:
        """Generate product-specific features."""
        product_id = event["product_id"]

        if product_id not in self.product_features:
            self.product_features[product_id] = {
                "view_count": 0,
                "purchase_count": 0,
                "total_revenue": 0.0,
                "unique_viewers": set(),
                "first_seen": current_time,
            }

        product_state = self.product_features[product_id]
        product_state["unique_viewers"].add(event["user_id"])

        if event["action"] == "view":
            product_state["view_count"] += 1
        elif event["action"] == "purchase":
            product_state["purchase_count"] += 1
            product_state["total_revenue"] += event["total_amount"]

        time_since_first_seen = current_time - product_state["first_seen"]

        return {
            "view_count": product_state["view_count"],
            "purchase_count": product_state["purchase_count"],
            "total_revenue": product_state["total_revenue"],
            "unique_viewers": len(product_state["unique_viewers"]),
            "conversion_rate": product_state["purchase_count"]
            / max(product_state["view_count"], 1),
            "revenue_per_view": product_state["total_revenue"]
            / max(product_state["view_count"], 1),
            "time_since_first_seen_ms": time_since_first_seen,
            "is_popular": product_state["view_count"] > 50,
            "category": event["category"],
        }

    def _generate_session_features(self, event: dict, current_time: int) -> dict:
        """Generate session-specific features."""
        session_id = event["session_id"]

        if session_id not in self.session_features:
            self.session_features[session_id] = {
                "event_count": 0,
                "start_time": current_time,
                "actions": [],
                "categories": set(),
                "total_spent": 0.0,
            }

        session_state = self.session_features[session_id]
        session_state["event_count"] += 1
        session_state["actions"].append(event["action"])
        session_state["categories"].add(event["category"])

        if event["action"] == "purchase":
            session_state["total_spent"] += event["total_amount"]

        session_duration = current_time - session_state["start_time"]

        return {
            "event_count": session_state["event_count"],
            "session_duration_ms": session_duration,
            "unique_categories": len(session_state["categories"]),
            "total_spent": session_state["total_spent"],
            "avg_time_per_event": session_duration
            / max(session_state["event_count"], 1),
            "has_purchase": "purchase" in session_state["actions"],
            "action_diversity": len(set(session_state["actions"])),
            "last_action": (
                session_state["actions"][-1] if session_state["actions"] else "unknown"
            ),
        }


@handle_errors
def setup_state_management_pipelines(
    stream, state_types: List[str], state_ttl_hours: int
):
    """
    Setup various state management pipelines.

    Args:
        stream: Input event stream
        state_types: List of state types to create
        state_ttl_hours: TTL for state in hours

    Returns:
        Dictionary of state management streams
    """
    print(f"\n🔄 Setting up state management pipelines...")
    print(f"   State types: {state_types}")
    print(f"   State TTL: {state_ttl_hours} hours")

    state_streams = {}

    # Parse events first
    from streaming_analytics import EventParsingFunction

    parsed_stream = stream.map(EventParsingFunction())

    # 1. User Profile Management (ValueState)
    if "keyed" in state_types or "user_profiles" in state_types or "all" in state_types:
        print("   Creating user profile management...")
        profile_stream = parsed_stream.key_by(lambda event: event["user_id"]).process(
            UserProfileManager(state_ttl_hours)
        )

        state_streams["user_profiles"] = profile_stream

    # 2. Session Analysis (ListState)
    if "keyed" in state_types or "sessions" in state_types or "all" in state_types:
        print("   Creating session analysis...")
        session_stream = parsed_stream.key_by(lambda event: event["user_id"]).process(
            SessionAnalyzer(session_timeout_minutes=30)
        )

        state_streams["sessions"] = session_stream

    # 3. Product Popularity Tracking (MapState)
    if "keyed" in state_types or "products" in state_types or "all" in state_types:
        print("   Creating product popularity tracking...")
        popularity_stream = parsed_stream.key_by(
            lambda event: event["product_id"]
        ).process(ProductPopularityTracker(window_hours=1))

        state_streams["product_popularity"] = popularity_stream

    # 4. Feature Store Processing (Complex State)
    if "complex" in state_types or "features" in state_types or "all" in state_types:
        print("   Creating feature store processing...")
        feature_stream = parsed_stream.process(FeatureStoreProcessor())

        state_streams["features"] = feature_stream

    print("✅ State management pipelines configured")
    return state_streams


@handle_errors
def setup_state_outputs(state_streams: dict, kafka_servers: str, output_path: str):
    """
    Setup outputs for state management streams.

    Args:
        state_streams: Dictionary of state streams
        kafka_servers: Kafka bootstrap servers
        output_path: Base output path
    """
    print(f"\n🔄 Setting up state management outputs...")

    for stream_type, stream in state_streams.items():
        # Console output for monitoring
        stream.print(f"STATE_{stream_type.upper()}")

        # Kafka output
        kafka_topic = f"state-{stream_type}"
        kafka_sink = create_kafka_sink(kafka_topic, kafka_servers)

        # Convert to JSON and send to Kafka
        stream.map(lambda result: json.dumps(result, default=str)).add_sink(kafka_sink)

        print(f"   {stream_type} state -> topic: {kafka_topic}")

    print("✅ State management outputs configured")


@handle_errors
def monitor_state_management_job(env: StreamExecutionEnvironment, duration: int):
    """
    Monitor state management job execution.

    Args:
        env: StreamExecutionEnvironment
        duration: How long to monitor
    """
    print(f"\n📊 Monitoring state management job for {duration} seconds...")

    start_time = time.time()
    end_time = start_time + duration

    # Start job
    job_result = env.execute_async("FlinkStateManagement")

    # Setup signal handler
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal, stopping job...")
        try:
            job_result.cancel()
        except:
            pass
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while time.time() < end_time and not job_result.is_done():
            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            print(f"\n⏱️  Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")

            # Print metrics
            metrics = metrics_tracker.get_metrics()
            print(f"   Profiles updated: {metrics.get('profiles_updated', 0)}")
            print(f"   Session updates: {metrics.get('session_updates', 0)}")
            print(f"   Sessions completed: {metrics.get('sessions_completed', 0)}")
            print(f"   Popularity updates: {metrics.get('popularity_updates', 0)}")
            print(f"   Features generated: {metrics.get('features_generated', 0)}")
            print(f"   Tier upgrades: {metrics.get('tier_upgrades', 0)}")
            print(f"   State cleanups: {metrics.get('state_cleanups', 0)}")

            if job_result.is_done():
                print("   Job Status: COMPLETED")
                break
            else:
                print("   Job Status: RUNNING")
                print("   State Backend: RocksDB (configured for persistence)")

            time.sleep(15)

    except KeyboardInterrupt:
        print("\n⚠️  Job monitoring interrupted")
        try:
            job_result.cancel()
        except:
            pass

    finally:
        if not job_result.is_done():
            print("\n🔄 Cancelling job...")
            try:
                job_result.cancel()
            except:
                pass

    print("✅ State management job monitoring completed")


@handle_errors
def main():
    """Main state management workflow."""
    # Parse arguments
    parser = parse_common_args()
    parser.add_argument(
        "--state-types",
        default="keyed,complex",
        help="Comma-separated state types to create",
    )
    parser.add_argument("--state-ttl", type=int, default=24, help="State TTL in hours")
    parser.add_argument(
        "--enable-cep", action="store_true", help="Enable complex event processing"
    )
    args = parser.parse_args()

    print("🚀 Starting Flink Advanced State Management")
    print(f"   Application: {args.app_name}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   State types: {args.state_types}")
    print(f"   State TTL: {args.state_ttl} hours")
    print(f"   Enable CEP: {args.enable_cep}")

    # Create configuration with optimized settings for state management
    config = FlinkConfig(
        app_name=f"{args.app_name}_StateManagement",
        parallelism=args.parallelism,
        kafka_servers=args.kafka_servers,
        state_backend="rocksdb",  # Use RocksDB for state persistence
        managed_memory_fraction=0.6,  # Increase managed memory for state
    )

    # Create environment
    env = create_flink_environment(config)

    # Configure for state management
    env.get_config().set_auto_watermark_interval(200)

    try:
        # Setup data source
        print("\n🔄 Setting up data source...")

        # Use sample data generator for consistent state management examples
        sample_stream = generate_sample_streaming_data(
            env,
            rate_per_second=30,  # 30 events per second for richer state
            total_records=args.duration * 30,
        )

        # Set watermark strategy
        watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(
            Duration.of_seconds(20)
        )

        event_stream = sample_stream.assign_timestamps_and_watermarks(
            watermark_strategy
        )

        # Setup state management pipelines
        state_types = args.state_types.split(",")
        state_streams = setup_state_management_pipelines(
            event_stream, state_types, args.state_ttl
        )

        # Setup outputs
        setup_state_outputs(state_streams, config.kafka_servers, args.output_path)

        # Monitor job progress
        monitor_job_progress(env, "Advanced State Management")

        print(f"\n📊 Created {len(state_streams)} state management pipelines:")
        for stream_type in state_streams.keys():
            print(f"   - {stream_type}")

        print("\n💡 State Management Features:")
        print("   - User profile tracking with ValueState and TTL")
        print("   - Session analysis with ListState and timers")
        print("   - Product popularity with MapState and cleanup")
        print("   - Real-time feature generation for ML")
        print("   - Automatic state cleanup and TTL management")
        print("   - RocksDB state backend for persistence")

        # Monitor job
        monitor_state_management_job(env, args.duration)

        # Print final metrics
        metrics_tracker.print_summary()

        print(f"\n✅ State management completed!")
        print(
            f"   Processed {len(state_streams)} state types for {args.duration} seconds"
        )
        print(f"   State persisted in RocksDB with {args.state_ttl}h TTL")
        print(f"   Results available in Kafka topics")
        print(f"   Flink Web UI: http://192.168.1.184:8081")

    except KeyboardInterrupt:
        print("\n⚠️  State management interrupted by user")
    except Exception as e:
        print(f"\n❌ State management error: {e}")
        raise
    finally:
        cleanup_environment(env)


if __name__ == "__main__":
    main()
