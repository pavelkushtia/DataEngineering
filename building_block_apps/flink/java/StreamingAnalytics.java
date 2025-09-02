/*
 * Flink Streaming Analytics - Java Building Block Application
 *
 * This class demonstrates comprehensive real-time stream processing with Apache Flink in Java:
 * - Real-time event processing from Kafka
 * - Complex windowing and aggregations
 * - Stateful operations and pattern detection
 * - Event time processing with watermarks
 * - Multiple output sinks and monitoring
 *
 * Usage:
 *    bazel run //flink/java:StreamingAnalytics -- --input-topic events --duration 120
 *
 * Examples:
 *    # Basic streaming analytics
 *    bazel run //flink/java:StreamingAnalytics
 *    
 *    # Custom topic and duration
 *    bazel run //flink/java:StreamingAnalytics -- --input-topic user-events --duration 300
 */

package com.dataengineering.flink;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.typeinfo.TypeHint;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.assigners.SlidingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

/**
 * Main class for Flink Streaming Analytics building block application.
 */
public class StreamingAnalytics {
    
    private static final String DEFAULT_KAFKA_SERVERS = "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092";
    private static final String DEFAULT_INPUT_TOPIC = "flink-events";
    private static final String DEFAULT_OUTPUT_TOPIC = "analytics-results";
    private static final String DEFAULT_GROUP_ID = "flink-java-analytics";
    
    public static void main(String[] args) throws Exception {
        // Parse parameters
        final ParameterTool params = ParameterTool.fromArgs(args);
        
        System.out.println("🚀 Starting Flink Java Streaming Analytics");
        System.out.println("   Input topic: " + params.get("input-topic", DEFAULT_INPUT_TOPIC));
        System.out.println("   Output topic: " + params.get("output-topic", DEFAULT_OUTPUT_TOPIC));
        System.out.println("   Kafka servers: " + params.get("kafka-servers", DEFAULT_KAFKA_SERVERS));
        System.out.println("   Parallelism: " + params.getInt("parallelism", 4));
        
        // Setup execution environment
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(params.getInt("parallelism", 4));
        
        // Enable checkpointing
        env.enableCheckpointing(10000); // 10 seconds
        
        // Create Kafka source
        KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
                .setBootstrapServers(params.get("kafka-servers", DEFAULT_KAFKA_SERVERS))
                .setTopics(params.get("input-topic", DEFAULT_INPUT_TOPIC))
                .setGroupId(params.get("group-id", DEFAULT_GROUP_ID))
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();
        
        // Create data stream
        DataStream<String> rawStream = env.fromSource(
                kafkaSource,
                WatermarkStrategy.<String>forBoundedOutOfOrderness(Duration.ofSeconds(20))
                        .withTimestampAssigner((event, timestamp) -> extractEventTime(event)),
                "Kafka Source"
        );
        
        // Parse JSON events
        DataStream<EventData> eventStream = rawStream
                .map(new EventParsingFunction())
                .name("Parse Events");
        
        // Real-time analytics pipeline
        createAnalyticsPipeline(eventStream, params);
        
        // Execute the job
        System.out.println("✅ Starting Flink job...");
        env.execute("Flink Java Streaming Analytics");
    }
    
    /**
     * Create comprehensive analytics pipeline.
     */
    private static void createAnalyticsPipeline(DataStream<EventData> eventStream, ParameterTool params) {
        
        // 1. Real-time revenue tracking (1-minute tumbling windows)
        DataStream<RevenueMetrics> revenueStream = eventStream
                .keyBy(EventData::getCategory)
                .window(TumblingEventTimeWindows.of(Time.minutes(1)))
                .aggregate(new RevenueAggregator(), new RevenueWindowFunction())
                .name("Revenue Analytics");
        
        // 2. User behavior tracking with state
        DataStream<UserBehaviorMetrics> behaviorStream = eventStream
                .keyBy(EventData::getUserId)
                .process(new UserBehaviorTracker())
                .name("User Behavior Tracking");
        
        // 3. Product popularity (5-minute sliding windows)
        DataStream<ProductMetrics> popularityStream = eventStream
                .filter(event -> "purchase".equals(event.getAction()) || "view".equals(event.getAction()))
                .keyBy(EventData::getProductId)
                .window(SlidingEventTimeWindows.of(Time.minutes(5), Time.minutes(1)))
                .aggregate(new ProductAggregator(), new ProductWindowFunction())
                .name("Product Popularity");
        
        // 4. Fraud detection
        DataStream<FraudAlert> fraudStream = eventStream
                .filter(event -> event.getTotalAmount() > 500)
                .keyBy(EventData::getUserId)
                .process(new FraudDetector())
                .name("Fraud Detection");
        
        // Setup outputs
        setupOutputSinks(revenueStream, behaviorStream, popularityStream, fraudStream, params);
        
        // Console outputs for monitoring
        revenueStream.print("REVENUE").setParallelism(1);
        fraudStream.print("FRAUD_ALERT").setParallelism(1);
    }
    
    /**
     * Setup output sinks for analytics results.
     */
    private static void setupOutputSinks(
            DataStream<RevenueMetrics> revenueStream,
            DataStream<UserBehaviorMetrics> behaviorStream,
            DataStream<ProductMetrics> popularityStream,
            DataStream<FraudAlert> fraudStream,
            ParameterTool params) {
        
        String kafkaServers = params.get("kafka-servers", DEFAULT_KAFKA_SERVERS);
        
        // Revenue metrics to Kafka
        KafkaSink<String> revenueSink = KafkaSink.<String>builder()
                .setBootstrapServers(kafkaServers)
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic("revenue-metrics")
                        .setValueSerializationSchema(new SimpleStringSchema())
                        .build())
                .build();
        
        revenueStream
                .map(metrics -> metrics.toJson())
                .sinkTo(revenueSink)
                .name("Revenue Kafka Sink");
        
        // Fraud alerts to Kafka
        KafkaSink<String> fraudSink = KafkaSink.<String>builder()
                .setBootstrapServers(kafkaServers)
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic("fraud-alerts")
                        .setValueSerializationSchema(new SimpleStringSchema())
                        .build())
                .build();
        
        fraudStream
                .map(alert -> alert.toJson())
                .sinkTo(fraudSink)
                .name("Fraud Kafka Sink");
    }
    
    /**
     * Extract event time from JSON string.
     */
    private static long extractEventTime(String jsonEvent) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode node = mapper.readTree(jsonEvent);
            String timestamp = node.get("timestamp").asText();
            return Instant.parse(timestamp + "Z").toEpochMilli();
        } catch (Exception e) {
            return System.currentTimeMillis();
        }
    }
    
    // ========== Data Classes ==========
    
    /**
     * Event data class.
     */
    public static class EventData {
        public String eventId;
        public String userId;
        public String sessionId;
        public String productId;
        public String category;
        public String action;
        public double price;
        public int quantity;
        public String timestamp;
        public long eventTime;
        
        public EventData() {}
        
        public EventData(String eventId, String userId, String sessionId, String productId,
                        String category, String action, double price, int quantity, String timestamp) {
            this.eventId = eventId;
            this.userId = userId;
            this.sessionId = sessionId;
            this.productId = productId;
            this.category = category;
            this.action = action;
            this.price = price;
            this.quantity = quantity;
            this.timestamp = timestamp;
            this.eventTime = extractEventTime(timestamp);
        }
        
        public double getTotalAmount() {
            return price * quantity;
        }
        
        // Getters for KeyBy operations
        public String getCategory() { return category; }
        public String getUserId() { return userId; }
        public String getProductId() { return productId; }
        public String getAction() { return action; }
        
        private long extractEventTime(String timestamp) {
            try {
                return Instant.parse(timestamp + "Z").toEpochMilli();
            } catch (Exception e) {
                return System.currentTimeMillis();
            }
        }
    }
    
    /**
     * Revenue metrics class.
     */
    public static class RevenueMetrics {
        public String category;
        public long windowStart;
        public long windowEnd;
        public double totalRevenue;
        public long orderCount;
        public long uniqueUsers;
        public double avgOrderValue;
        public double maxOrderValue;
        
        public String toJson() {
            return String.format(
                "{\"category\":\"%s\",\"windowStart\":%d,\"windowEnd\":%d," +
                "\"totalRevenue\":%.2f,\"orderCount\":%d,\"uniqueUsers\":%d," +
                "\"avgOrderValue\":%.2f,\"maxOrderValue\":%.2f}",
                category, windowStart, windowEnd, totalRevenue, orderCount, 
                uniqueUsers, avgOrderValue, maxOrderValue
            );
        }
    }
    
    /**
     * User behavior metrics class.
     */
    public static class UserBehaviorMetrics {
        public String userId;
        public long totalEvents;
        public double totalSpent;
        public long sessionCount;
        public long lastActivity;
        public String userTier;
        
        public String toJson() {
            return String.format(
                "{\"userId\":\"%s\",\"totalEvents\":%d,\"totalSpent\":%.2f," +
                "\"sessionCount\":%d,\"lastActivity\":%d,\"userTier\":\"%s\"}",
                userId, totalEvents, totalSpent, sessionCount, lastActivity, userTier
            );
        }
    }
    
    /**
     * Product metrics class.
     */
    public static class ProductMetrics {
        public String productId;
        public String category;
        public long viewCount;
        public long purchaseCount;
        public double totalRevenue;
        public double conversionRate;
        
        public String toJson() {
            return String.format(
                "{\"productId\":\"%s\",\"category\":\"%s\",\"viewCount\":%d," +
                "\"purchaseCount\":%d,\"totalRevenue\":%.2f,\"conversionRate\":%.4f}",
                productId, category, viewCount, purchaseCount, totalRevenue, conversionRate
            );
        }
    }
    
    /**
     * Fraud alert class.
     */
    public static class FraudAlert {
        public String userId;
        public String eventId;
        public double amount;
        public String alertType;
        public int fraudScore;
        public long alertTime;
        
        public String toJson() {
            return String.format(
                "{\"userId\":\"%s\",\"eventId\":\"%s\",\"amount\":%.2f," +
                "\"alertType\":\"%s\",\"fraudScore\":%d,\"alertTime\":%d}",
                userId, eventId, amount, alertType, fraudScore, alertTime
            );
        }
    }
    
    // ========== Functions ==========
    
    /**
     * Parse JSON events into EventData objects.
     */
    public static class EventParsingFunction implements MapFunction<String, EventData> {
        private static final ObjectMapper mapper = new ObjectMapper();
        
        @Override
        public EventData map(String jsonString) throws Exception {
            try {
                JsonNode node = mapper.readTree(jsonString);
                return new EventData(
                    node.get("event_id").asText(),
                    node.get("user_id").asText(),
                    node.get("session_id").asText(),
                    node.get("product_id").asText(),
                    node.get("category").asText(),
                    node.get("action").asText(),
                    node.get("price").asDouble(),
                    node.get("quantity").asInt(),
                    node.get("timestamp").asText()
                );
            } catch (Exception e) {
                // Return default event for malformed data
                return new EventData("invalid", "unknown", "unknown", "unknown", 
                                   "unknown", "unknown", 0.0, 0, 
                                   Instant.now().toString());
            }
        }
    }
    
    /**
     * Aggregate revenue metrics.
     */
    public static class RevenueAggregator implements AggregateFunction<EventData, RevenueAggregator.Accumulator, RevenueAggregator.Accumulator> {
        
        public static class Accumulator {
            public double totalRevenue = 0.0;
            public long orderCount = 0;
            public Map<String, Double> userSpending = new HashMap<>();
            public double maxOrderValue = 0.0;
        }
        
        @Override
        public Accumulator createAccumulator() {
            return new Accumulator();
        }
        
        @Override
        public Accumulator add(EventData event, Accumulator acc) {
            if ("purchase".equals(event.getAction())) {
                double amount = event.getTotalAmount();
                acc.totalRevenue += amount;
                acc.orderCount++;
                acc.userSpending.put(event.getUserId(), 
                    acc.userSpending.getOrDefault(event.getUserId(), 0.0) + amount);
                acc.maxOrderValue = Math.max(acc.maxOrderValue, amount);
            }
            return acc;
        }
        
        @Override
        public Accumulator getResult(Accumulator acc) {
            return acc;
        }
        
        @Override
        public Accumulator merge(Accumulator acc1, Accumulator acc2) {
            Accumulator merged = new Accumulator();
            merged.totalRevenue = acc1.totalRevenue + acc2.totalRevenue;
            merged.orderCount = acc1.orderCount + acc2.orderCount;
            merged.maxOrderValue = Math.max(acc1.maxOrderValue, acc2.maxOrderValue);
            
            // Merge user spending maps
            merged.userSpending.putAll(acc1.userSpending);
            acc2.userSpending.forEach((user, amount) ->
                merged.userSpending.merge(user, amount, Double::sum));
            
            return merged;
        }
    }
    
    /**
     * Process window function for revenue metrics.
     */
    public static class RevenueWindowFunction extends ProcessWindowFunction<RevenueAggregator.Accumulator, RevenueMetrics, String, TimeWindow> {
        
        @Override
        public void process(String key, Context context, Iterable<RevenueAggregator.Accumulator> elements, Collector<RevenueMetrics> out) {
            RevenueAggregator.Accumulator acc = elements.iterator().next();
            
            RevenueMetrics metrics = new RevenueMetrics();
            metrics.category = key;
            metrics.windowStart = context.window().getStart();
            metrics.windowEnd = context.window().getEnd();
            metrics.totalRevenue = acc.totalRevenue;
            metrics.orderCount = acc.orderCount;
            metrics.uniqueUsers = acc.userSpending.size();
            metrics.avgOrderValue = acc.orderCount > 0 ? acc.totalRevenue / acc.orderCount : 0.0;
            metrics.maxOrderValue = acc.maxOrderValue;
            
            out.collect(metrics);
        }
    }
    
    /**
     * Product aggregator.
     */
    public static class ProductAggregator implements AggregateFunction<EventData, ProductAggregator.Accumulator, ProductAggregator.Accumulator> {
        
        public static class Accumulator {
            public long viewCount = 0;
            public long purchaseCount = 0;
            public double totalRevenue = 0.0;
            public String category = "";
        }
        
        @Override
        public Accumulator createAccumulator() {
            return new Accumulator();
        }
        
        @Override
        public Accumulator add(EventData event, Accumulator acc) {
            acc.category = event.getCategory();
            
            if ("view".equals(event.getAction())) {
                acc.viewCount++;
            } else if ("purchase".equals(event.getAction())) {
                acc.purchaseCount++;
                acc.totalRevenue += event.getTotalAmount();
            }
            return acc;
        }
        
        @Override
        public Accumulator getResult(Accumulator acc) {
            return acc;
        }
        
        @Override
        public Accumulator merge(Accumulator acc1, Accumulator acc2) {
            Accumulator merged = new Accumulator();
            merged.viewCount = acc1.viewCount + acc2.viewCount;
            merged.purchaseCount = acc1.purchaseCount + acc2.purchaseCount;
            merged.totalRevenue = acc1.totalRevenue + acc2.totalRevenue;
            merged.category = acc1.category.isEmpty() ? acc2.category : acc1.category;
            return merged;
        }
    }
    
    /**
     * Product window function.
     */
    public static class ProductWindowFunction extends ProcessWindowFunction<ProductAggregator.Accumulator, ProductMetrics, String, TimeWindow> {
        
        @Override
        public void process(String key, Context context, Iterable<ProductAggregator.Accumulator> elements, Collector<ProductMetrics> out) {
            ProductAggregator.Accumulator acc = elements.iterator().next();
            
            ProductMetrics metrics = new ProductMetrics();
            metrics.productId = key;
            metrics.category = acc.category;
            metrics.viewCount = acc.viewCount;
            metrics.purchaseCount = acc.purchaseCount;
            metrics.totalRevenue = acc.totalRevenue;
            metrics.conversionRate = acc.viewCount > 0 ? (double) acc.purchaseCount / acc.viewCount : 0.0;
            
            out.collect(metrics);
        }
    }
    
    /**
     * User behavior tracker with state.
     */
    public static class UserBehaviorTracker extends KeyedProcessFunction<String, EventData, UserBehaviorMetrics> {
        
        private ValueState<UserBehaviorMetrics> behaviorState;
        
        @Override
        public void open(Configuration parameters) {
            ValueStateDescriptor<UserBehaviorMetrics> descriptor = new ValueStateDescriptor<>(
                "userBehavior",
                TypeInformation.of(new TypeHint<UserBehaviorMetrics>() {})
            );
            behaviorState = getRuntimeContext().getState(descriptor);
        }
        
        @Override
        public void processElement(EventData event, Context ctx, Collector<UserBehaviorMetrics> out) throws Exception {
            UserBehaviorMetrics current = behaviorState.value();
            if (current == null) {
                current = new UserBehaviorMetrics();
                current.userId = event.getUserId();
            }
            
            // Update metrics
            current.totalEvents++;
            current.lastActivity = ctx.timestamp();
            
            if ("purchase".equals(event.getAction())) {
                current.totalSpent += event.getTotalAmount();
            }
            
            // Update user tier based on spending
            if (current.totalSpent >= 2000) {
                current.userTier = "GOLD";
            } else if (current.totalSpent >= 500) {
                current.userTier = "SILVER";
            } else {
                current.userTier = "BRONZE";
            }
            
            // Update state and emit
            behaviorState.update(current);
            out.collect(current);
        }
    }
    
    /**
     * Fraud detector with stateful processing.
     */
    public static class FraudDetector extends KeyedProcessFunction<String, EventData, FraudAlert> {
        
        private ValueState<Long> lastTransactionTime;
        private ValueState<Double> recentSpending;
        
        @Override
        public void open(Configuration parameters) {
            ValueStateDescriptor<Long> timeDescriptor = new ValueStateDescriptor<>(
                "lastTransactionTime",
                TypeInformation.of(new TypeHint<Long>() {})
            );
            lastTransactionTime = getRuntimeContext().getState(timeDescriptor);
            
            ValueStateDescriptor<Double> spendingDescriptor = new ValueStateDescriptor<>(
                "recentSpending", 
                TypeInformation.of(new TypeHint<Double>() {})
            );
            recentSpending = getRuntimeContext().getState(spendingDescriptor);
        }
        
        @Override
        public void processElement(EventData event, Context ctx, Collector<FraudAlert> out) throws Exception {
            Long lastTime = lastTransactionTime.value();
            Double spending = recentSpending.value();
            
            if (spending == null) spending = 0.0;
            
            long currentTime = ctx.timestamp();
            double amount = event.getTotalAmount();
            
            // Reset spending if more than 1 hour passed
            if (lastTime != null && currentTime - lastTime > 3600000) { // 1 hour
                spending = 0.0;
            }
            
            spending += amount;
            
            // Fraud detection logic
            int fraudScore = 0;
            String alertType = "SUSPICIOUS";
            
            if (amount > 1000) {
                fraudScore += 50;
                alertType = "HIGH_VALUE";
            }
            
            if (spending > 2000) {
                fraudScore += 30;
                alertType = "HIGH_VOLUME";
            }
            
            if (lastTime != null && currentTime - lastTime < 60000) { // 1 minute
                fraudScore += 40;
                alertType = "RAPID_TRANSACTIONS";
            }
            
            // Emit alert if fraud score is high
            if (fraudScore >= 40) {
                FraudAlert alert = new FraudAlert();
                alert.userId = event.getUserId();
                alert.eventId = event.eventId;
                alert.amount = amount;
                alert.alertType = alertType;
                alert.fraudScore = fraudScore;
                alert.alertTime = currentTime;
                
                out.collect(alert);
            }
            
            // Update state
            lastTransactionTime.update(currentTime);
            recentSpending.update(spending);
        }
    }
}
