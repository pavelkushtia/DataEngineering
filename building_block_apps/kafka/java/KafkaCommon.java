import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.Arrays;
import java.util.Properties;

/**
 * Common utilities for Kafka Java examples.
 * 
 * This class provides shared configuration and utilities for Kafka producers and consumers.
 */
public class KafkaCommon {
    private static final Logger logger = LoggerFactory.getLogger(KafkaCommon.class);
    
    // Kafka cluster configuration
    private static final String BOOTSTRAP_SERVERS = "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092";
    private static final String DEFAULT_TOPIC = "building-blocks-demo";
    
    /**
     * Get common Kafka configuration properties.
     * 
     * @return Properties containing common Kafka configuration
     */
    public static Properties getCommonConfig() {
        Properties props = new Properties();
        props.put("bootstrap.servers", BOOTSTRAP_SERVERS);
        props.put("security.protocol", "PLAINTEXT");
        props.put("acks", "all");
        props.put("retries", 3);
        props.put("retry.backoff.ms", 100);
        props.put("request.timeout.ms", 30000);
        props.put("delivery.timeout.ms", 120000);
        return props;
    }
    
    /**
     * Get Kafka producer specific configuration.
     * 
     * @return Properties containing producer configuration
     */
    public static Properties getProducerConfig() {
        Properties props = getCommonConfig();
        
        // Producer specific settings
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);
        props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");
        props.put(ProducerConfig.BATCH_SIZE_CONFIG, 16384);
        props.put(ProducerConfig.LINGER_MS_CONFIG, 10);
        props.put(ProducerConfig.BUFFER_MEMORY_CONFIG, 33554432);
        
        return props;
    }
    
    /**
     * Get Kafka consumer specific configuration.
     * 
     * @param groupId Consumer group identifier
     * @return Properties containing consumer configuration
     */
    public static Properties getConsumerConfig(String groupId) {
        Properties props = getCommonConfig();
        
        // Consumer specific settings
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
        props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, 1000);
        props.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, 30000);
        props.put(ConsumerConfig.HEARTBEAT_INTERVAL_MS_CONFIG, 3000);
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500);
        props.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, 300000);
        
        return props;
    }
    
    /**
     * Create a sample JSON message for testing.
     * 
     * @param messageId Unique identifier for the message
     * @param messageType Type of message being created
     * @return JSON string representation of the message
     */
    public static String createSampleMessage(int messageId, String messageType) {
        long timestamp = Instant.now().toEpochMilli();
        
        // Create JSON manually for simplicity (avoiding external JSON libraries)
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"id\":").append(messageId).append(",");
        json.append("\"type\":\"").append(messageType).append("\",");
        json.append("\"timestamp\":").append(timestamp).append(",");
        json.append("\"data\":{");
        json.append("\"user_id\":\"user_").append(messageId % 1000).append("\",");
        json.append("\"action\":\"").append(messageId % 2 == 0 ? "view_product" : "add_to_cart").append("\",");
        json.append("\"product_id\":\"product_").append(messageId % 100).append("\",");
        json.append("\"session_id\":\"session_").append(messageId / 10).append("\",");
        json.append("\"value\":").append(Math.round((messageId * 1.23) % 1000 * 100.0) / 100.0);
        json.append("},");
        json.append("\"metadata\":{");
        json.append("\"source\":\"java_producer\",");
        json.append("\"version\":\"1.0\",");
        json.append("\"environment\":\"development\"");
        json.append("}");
        json.append("}");
        
        return json.toString();
    }
    
    /**
     * Get the default topic name for examples.
     * 
     * @return Default topic name
     */
    public static String getDefaultTopic() {
        return DEFAULT_TOPIC;
    }
    
    /**
     * Get the bootstrap servers configuration.
     * 
     * @return Bootstrap servers string
     */
    public static String getBootstrapServers() {
        return BOOTSTRAP_SERVERS;
    }
    
    /**
     * Simple statistics tracker for messages.
     */
    public static class MessageStats {
        private int sentCount = 0;
        private int receivedCount = 0;
        private int errorCount = 0;
        private final long startTime;
        
        public MessageStats() {
            this.startTime = System.currentTimeMillis();
        }
        
        public synchronized void recordSent() {
            sentCount++;
        }
        
        public synchronized void recordReceived() {
            receivedCount++;
        }
        
        public synchronized void recordError() {
            errorCount++;
        }
        
        public synchronized void printStats() {
            long elapsed = (System.currentTimeMillis() - startTime) / 1000;
            double sendRate = elapsed > 0 ? (double) sentCount / elapsed : 0;
            double receiveRate = elapsed > 0 ? (double) receivedCount / elapsed : 0;
            
            System.out.printf("📊 Stats: Sent=%d, Received=%d, Errors=%d, Elapsed=%ds, " +
                            "Send Rate=%.2f/s, Receive Rate=%.2f/s%n",
                            sentCount, receivedCount, errorCount, elapsed, sendRate, receiveRate);
        }
        
        public synchronized int getSentCount() { return sentCount; }
        public synchronized int getReceivedCount() { return receivedCount; }
        public synchronized int getErrorCount() { return errorCount; }
    }
    
    /**
     * Parse command line arguments into a simple map-like structure.
     */
    public static class Args {
        private final String[] args;
        
        public Args(String[] args) {
            this.args = args;
        }
        
        public String get(String flag, String defaultValue) {
            for (int i = 0; i < args.length - 1; i++) {
                if (args[i].equals(flag)) {
                    return args[i + 1];
                }
            }
            return defaultValue;
        }
        
        public int getInt(String flag, int defaultValue) {
            String value = get(flag, String.valueOf(defaultValue));
            try {
                return Integer.parseInt(value);
            } catch (NumberFormatException e) {
                logger.warn("Invalid integer value for {}: {}, using default: {}", flag, value, defaultValue);
                return defaultValue;
            }
        }
        
        public double getDouble(String flag, double defaultValue) {
            String value = get(flag, String.valueOf(defaultValue));
            try {
                return Double.parseDouble(value);
            } catch (NumberFormatException e) {
                logger.warn("Invalid double value for {}: {}, using default: {}", flag, value, defaultValue);
                return defaultValue;
            }
        }
        
        public boolean hasFlag(String flag) {
            return Arrays.asList(args).contains(flag);
        }
        
        public void printUsage(String programName) {
            System.out.println("Usage: " + programName + " [options]");
            System.out.println("Options:");
            System.out.println("  --topic TOPIC        Kafka topic (default: " + DEFAULT_TOPIC + ")");
            System.out.println("  --count COUNT        Number of messages (default: 10)");
            System.out.println("  --rate RATE          Messages per second (default: 1.0)");
            System.out.println("  --group GROUP        Consumer group ID (default: building-blocks-consumer-group)");
            System.out.println("  --timeout TIMEOUT    Timeout in seconds (default: infinite)");
            System.out.println("  --help               Show this help message");
        }
    }
}
