import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.clients.producer.Callback;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Kafka Producer Example in Java
 * 
 * This class demonstrates how to produce messages to a Kafka topic using the Kafka Java client.
 * It includes error handling, delivery confirmation, and performance monitoring.
 * 
 * Usage:
 *     java Producer [--topic TOPIC] [--count COUNT] [--rate RATE]
 * 
 * Example:
 *     java Producer --topic my-topic --count 1000 --rate 10
 */
public class Producer {
    private static final Logger logger = LoggerFactory.getLogger(Producer.class);
    private final String topic;
    private final KafkaProducer<String, String> producer;
    private final KafkaCommon.MessageStats stats;
    private final AtomicBoolean running;
    
    public Producer(String topic) {
        this.topic = topic;
        this.stats = new KafkaCommon.MessageStats();
        this.running = new AtomicBoolean(true);
        
        // Setup shutdown hook for graceful shutdown
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("🛑 Shutdown signal received, stopping gracefully...");
            running.set(false);
        }));
        
        // Create producer with configuration
        Properties config = KafkaCommon.getProducerConfig();
        this.producer = new KafkaProducer<>(config);
        
        logger.info("🔌 Connected to Kafka brokers: {}", KafkaCommon.getBootstrapServers());
        logger.info("✅ Producer initialized successfully!");
    }
    
    /**
     * Send a message to the Kafka topic with callback handling.
     * 
     * @param key Message key (for partitioning)
     * @param message Message content
     * @param latch CountDownLatch for synchronization
     */
    public void sendMessage(String key, String message, CountDownLatch latch) {
        try {
            ProducerRecord<String, String> record = new ProducerRecord<>(topic, key, message);
            
            producer.send(record, new Callback() {
                @Override
                public void onCompletion(RecordMetadata metadata, Exception exception) {
                    try {
                        if (exception == null) {
                            // Success
                            stats.recordSent();
                            logger.info("✅ Message sent to {}[{}] at offset {}", 
                                      metadata.topic(), metadata.partition(), metadata.offset());
                        } else {
                            // Error
                            stats.recordError();
                            logger.error("❌ Message delivery failed: {}", exception.getMessage());
                        }
                    } finally {
                        latch.countDown();
                    }
                }
            });
            
        } catch (Exception e) {
            logger.error("❌ Error sending message: {}", e.getMessage());
            stats.recordError();
            latch.countDown();
        }
    }
    
    /**
     * Produce a specified number of messages.
     * 
     * @param count Number of messages to produce
     * @param rate Messages per second (0 = no limit)
     */
    public void produceMessages(int count, double rate) {
        logger.info("🚀 Starting to produce {} messages to topic '{}'", count, topic);
        if (rate > 0) {
            logger.info("📊 Rate limit: {} messages/second", rate);
        } else {
            logger.info("📊 Rate limit: unlimited");
        }
        
        long sleepTimeMs = rate > 0 ? (long) (1000.0 / rate) : 0;
        CountDownLatch latch = new CountDownLatch(count);
        
        for (int i = 0; i < count && running.get(); i++) {
            // Create sample message
            String messageData = KafkaCommon.createSampleMessage(i, "producer_demo");
            String messageKey = "key_" + i;
            
            // Send message
            sendMessage(messageKey, messageData, latch);
            logger.info("📤 Sent message {}/{}: {}", i + 1, count, messageKey);
            
            // Rate limiting
            if (sleepTimeMs > 0) {
                try {
                    Thread.sleep(sleepTimeMs);
                } catch (InterruptedException e) {
                    logger.warn("Sleep interrupted, stopping...");
                    Thread.currentThread().interrupt();
                    break;
                }
            }
            
            // Print stats every 100 messages
            if ((i + 1) % 100 == 0) {
                stats.printStats();
            }
        }
        
        // Wait for all messages to be delivered
        logger.info("🔄 Waiting for all messages to be delivered...");
        try {
            latch.await();
        } catch (InterruptedException e) {
            logger.warn("Wait interrupted");
            Thread.currentThread().interrupt();
        }
        
        // Flush remaining messages
        logger.info("🔄 Flushing remaining messages...");
        producer.flush();
        
        logger.info("✅ Finished producing messages!");
        stats.printStats();
    }
    
    /**
     * Close the producer connection.
     */
    public void close() {
        if (producer != null) {
            logger.info("🔌 Closing producer connection...");
            producer.close();
            logger.info("✅ Producer closed successfully");
        }
    }
    
    /**
     * Main method to run the Kafka producer.
     * 
     * @param args Command line arguments
     */
    public static void main(String[] args) {
        KafkaCommon.Args parsedArgs = new KafkaCommon.Args(args);
        
        // Check for help flag
        if (parsedArgs.hasFlag("--help")) {
            parsedArgs.printUsage("Producer");
            return;
        }
        
        // Parse arguments
        String topic = parsedArgs.get("--topic", KafkaCommon.getDefaultTopic());
        int count = parsedArgs.getInt("--count", 10);
        double rate = parsedArgs.getDouble("--rate", 1.0);
        
        System.out.println("🎯 Kafka Producer Example");
        System.out.println("=".repeat(50));
        System.out.println("📌 Topic: " + topic);
        System.out.println("📊 Message count: " + count);
        System.out.println("⚡ Rate: " + rate + " messages/second");
        System.out.println("=".repeat(50));
        
        Producer producer = new Producer(topic);
        
        try {
            // Produce messages
            producer.produceMessages(count, rate);
            
        } catch (Exception e) {
            logger.error("❌ Unexpected error: {}", e.getMessage(), e);
            System.exit(1);
        } finally {
            producer.close();
        }
    }
}
