import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.TopicPartition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Collections;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

/**
 * Kafka Consumer Example in Java
 * 
 * This class demonstrates how to consume messages from a Kafka topic using the Kafka Java client.
 * It includes error handling, offset management, and performance monitoring.
 * 
 * Usage:
 *     java Consumer [--topic TOPIC] [--group GROUP] [--timeout TIMEOUT]
 * 
 * Example:
 *     java Consumer --topic my-topic --group my-consumer-group --timeout 60
 */
public class Consumer {
    private static final Logger logger = LoggerFactory.getLogger(Consumer.class);
    private final String topic;
    private final String groupId;
    private final KafkaConsumer<String, String> consumer;
    private final KafkaCommon.MessageStats stats;
    private final AtomicBoolean running;
    
    public Consumer(String topic, String groupId) {
        this.topic = topic;
        this.groupId = groupId;
        this.stats = new KafkaCommon.MessageStats();
        this.running = new AtomicBoolean(true);
        
        // Setup shutdown hook for graceful shutdown
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("🛑 Shutdown signal received, stopping gracefully...");
            running.set(false);
        }));
        
        // Create consumer with configuration
        Properties config = KafkaCommon.getConsumerConfig(groupId);
        this.consumer = new KafkaConsumer<>(config);
        
        // Subscribe to topic
        consumer.subscribe(Collections.singletonList(topic));
        
        logger.info("🔌 Connected to Kafka brokers: {}", KafkaCommon.getBootstrapServers());
        logger.info("👥 Consumer group: {}", groupId);
        logger.info("✅ Subscribed to topic '{}'!", topic);
    }
    
    /**
     * Process a received message.
     * 
     * @param record Kafka consumer record
     * @return true if processing successful, false otherwise
     */
    public boolean processMessage(ConsumerRecord<String, String> record) {
        try {
            // Extract message details
            String topic = record.topic();
            int partition = record.partition();
            long offset = record.offset();
            String key = record.key();
            String value = record.value();
            long timestamp = record.timestamp();
            
            stats.recordReceived();
            
            // Print message details
            logger.info("📨 Received message:");
            logger.info("   🔑 Key: {}", key);
            logger.info("   📋 Topic: {}[{}] @ offset {}", topic, partition, offset);
            logger.info("   ⏰ Timestamp: {}", timestamp);
            
            // Parse JSON message (simple regex-based parsing)
            String messageId = extractJsonField(value, "id");
            String messageType = extractJsonField(value, "type");
            
            logger.info("   📦 Message ID: {}", messageId != null ? messageId : "N/A");
            logger.info("   📊 Message Type: {}", messageType != null ? messageType : "N/A");
            
            // Process specific message types
            processMessageByType(value, messageType);
            
            return true;
            
        } catch (Exception e) {
            logger.error("❌ Error processing message: {}", e.getMessage());
            stats.recordError();
            return false;
        }
    }
    
    /**
     * Process message based on its type.
     * 
     * @param jsonMessage The full JSON message
     * @param messageType The message type
     */
    private void processMessageByType(String jsonMessage, String messageType) {
        if ("producer_demo".equals(messageType)) {
            String userId = extractNestedJsonField(jsonMessage, "data", "user_id");
            String action = extractNestedJsonField(jsonMessage, "data", "action");
            String productId = extractNestedJsonField(jsonMessage, "data", "product_id");
            String value = extractNestedJsonField(jsonMessage, "data", "value");
            
            logger.info("   👤 User: {}", userId);
            logger.info("   🎯 Action: {}", action);
            logger.info("   📦 Product: {}", productId);
            logger.info("   💰 Value: {}", value);
            
        } else if ("order".equals(messageType)) {
            String orderId = extractNestedJsonField(jsonMessage, "data", "order_id");
            String total = extractNestedJsonField(jsonMessage, "data", "total_amount");
            logger.info("   🛒 Order ID: {}", orderId);
            logger.info("   💵 Total: ${}", total);
            
        } else if ("user_event".equals(messageType)) {
            String eventName = extractNestedJsonField(jsonMessage, "data", "event_name");
            String sessionId = extractNestedJsonField(jsonMessage, "data", "session_id");
            logger.info("   📊 Event: {}", eventName);
            logger.info("   🔗 Session: {}", sessionId);
        }
        
        System.out.println(); // Empty line for readability
    }
    
    /**
     * Extract a field value from JSON string using simple regex.
     * 
     * @param json JSON string
     * @param fieldName Field name to extract
     * @return Field value or null if not found
     */
    private String extractJsonField(String json, String fieldName) {
        try {
            Pattern pattern = Pattern.compile("\"" + fieldName + "\"\\s*:\\s*\"?([^,}\"]+)\"?");
            Matcher matcher = pattern.matcher(json);
            if (matcher.find()) {
                return matcher.group(1).replaceAll("\"", "");
            }
        } catch (Exception e) {
            logger.debug("Failed to extract field '{}' from JSON", fieldName);
        }
        return null;
    }
    
    /**
     * Extract a nested field value from JSON string.
     * 
     * @param json JSON string
     * @param parentField Parent object field name
     * @param fieldName Field name to extract
     * @return Field value or null if not found
     */
    private String extractNestedJsonField(String json, String parentField, String fieldName) {
        try {
            // Find the parent object
            Pattern parentPattern = Pattern.compile("\"" + parentField + "\"\\s*:\\s*\\{([^}]+)\\}");
            Matcher parentMatcher = parentPattern.matcher(json);
            if (parentMatcher.find()) {
                String parentContent = parentMatcher.group(1);
                return extractJsonField(parentContent, fieldName);
            }
        } catch (Exception e) {
            logger.debug("Failed to extract nested field '{}.{}' from JSON", parentField, fieldName);
        }
        return null;
    }
    
    /**
     * Consume messages from the Kafka topic.
     * 
     * @param timeoutSeconds Maximum time to consume (null = infinite)
     */
    public void consumeMessages(Integer timeoutSeconds) {
        logger.info("🚀 Starting to consume from topic '{}'", topic);
        if (timeoutSeconds != null) {
            logger.info("⏰ Timeout: {} seconds", timeoutSeconds);
        } else {
            logger.info("⏰ Timeout: infinite (Ctrl+C to stop)");
        }
        System.out.println("=".repeat(50));
        
        long startTime = System.currentTimeMillis();
        long lastStatsTime = startTime;
        
        try {
            while (running.get()) {
                // Check timeout
                if (timeoutSeconds != null) {
                    long elapsed = (System.currentTimeMillis() - startTime) / 1000;
                    if (elapsed > timeoutSeconds) {
                        logger.info("⏰ Timeout reached ({}s)", timeoutSeconds);
                        break;
                    }
                }
                
                // Poll for messages
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));
                
                if (!records.isEmpty()) {
                    // Print partition assignment info (first time)
                    Set<TopicPartition> assignment = consumer.assignment();
                    if (!assignment.isEmpty()) {
                        logger.debug("📋 Assigned partitions: {}", assignment);
                    }
                    
                    // Process each message
                    for (ConsumerRecord<String, String> record : records) {
                        if (!running.get()) {
                            break;
                        }
                        processMessage(record);
                    }
                }
                
                // Print stats every 10 seconds
                long currentTime = System.currentTimeMillis();
                if (currentTime - lastStatsTime >= 10000) {
                    stats.printStats();
                    lastStatsTime = currentTime;
                }
            }
            
        } catch (Exception e) {
            logger.error("❌ Error during consumption: {}", e.getMessage());
            stats.recordError();
        }
        
        logger.info("✅ Finished consuming messages!");
        stats.printStats();
    }
    
    /**
     * Close the consumer connection.
     */
    public void close() {
        if (consumer != null) {
            logger.info("🔌 Closing consumer connection...");
            consumer.close();
            logger.info("✅ Consumer closed successfully");
        }
    }
    
    /**
     * Main method to run the Kafka consumer.
     * 
     * @param args Command line arguments
     */
    public static void main(String[] args) {
        KafkaCommon.Args parsedArgs = new KafkaCommon.Args(args);
        
        // Check for help flag
        if (parsedArgs.hasFlag("--help")) {
            parsedArgs.printUsage("Consumer");
            return;
        }
        
        // Parse arguments
        String topic = parsedArgs.get("--topic", KafkaCommon.getDefaultTopic());
        String group = parsedArgs.get("--group", "building-blocks-consumer-group");
        Integer timeout = null;
        String timeoutStr = parsedArgs.get("--timeout", null);
        if (timeoutStr != null) {
            try {
                timeout = Integer.parseInt(timeoutStr);
            } catch (NumberFormatException e) {
                logger.warn("Invalid timeout value: {}", timeoutStr);
            }
        }
        
        System.out.println("🎯 Kafka Consumer Example");
        System.out.println("=".repeat(50));
        System.out.println("📌 Topic: " + topic);
        System.out.println("👥 Group: " + group);
        System.out.println("⏰ Timeout: " + (timeout != null ? timeout + "s" : "infinite"));
        System.out.println("=".repeat(50));
        
        Consumer consumer = new Consumer(topic, group);
        
        try {
            // Consume messages
            consumer.consumeMessages(timeout);
            
        } catch (Exception e) {
            logger.error("❌ Unexpected error: {}", e.getMessage(), e);
            System.exit(1);
        } finally {
            consumer.close();
        }
    }
}
