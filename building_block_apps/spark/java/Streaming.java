import org.apache.spark.sql.SparkSession;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.streaming.StreamingQuery;
import org.apache.spark.sql.streaming.Trigger;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.types.DataTypes;
import org.apache.spark.sql.types.StructField;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.TimeoutException;

import static org.apache.spark.sql.functions.*;

/**
 * Spark Structured Streaming Examples - Building Block Application
 * 
 * This class demonstrates real-time data processing with Spark Structured Streaming in Java:
 * - Kafka stream processing
 * - Real-time aggregations with windowing
 * - Multiple output sinks (console, files)
 * - Watermarks for late data handling
 * 
 * Usage:
 *   bazel run //spark/java:Streaming -- --kafka-topic events --duration 120
 * 
 * Examples:
 *   # Basic streaming from Kafka
 *   bazel run //spark/java:Streaming
 *   
 *   # Custom topic and duration
 *   bazel run //spark/java:Streaming -- --kafka-topic user-events --duration 300
 */
public class Streaming {
    
    private static final Logger logger = LoggerFactory.getLogger(Streaming.class);
    
    /**
     * Define schema for incoming Kafka messages.
     */
    private static StructType getKafkaStreamSchema() {
        return DataTypes.createStructType(new StructField[] {
            DataTypes.createStructField("event_id", DataTypes.StringType, true),
            DataTypes.createStructField("user_id", DataTypes.StringType, true),
            DataTypes.createStructField("event_type", DataTypes.StringType, true),
            DataTypes.createStructField("product_id", DataTypes.StringType, true),
            DataTypes.createStructField("category", DataTypes.StringType, true),
            DataTypes.createStructField("price", DataTypes.DoubleType, true),
            DataTypes.createStructField("quantity", DataTypes.IntegerType, true),
            DataTypes.createStructField("session_id", DataTypes.StringType, true),
            DataTypes.createStructField("timestamp", DataTypes.StringType, true),
            DataTypes.createStructField("metadata", DataTypes.createStructType(new StructField[] {
                DataTypes.createStructField("source", DataTypes.StringType, true),
                DataTypes.createStructField("version", DataTypes.StringType, true),
                DataTypes.createStructField("user_agent", DataTypes.StringType, true),
                DataTypes.createStructField("ip_address", DataTypes.StringType, true)
            }), true)
        });
    }
    
    /**
     * Create a streaming Dataset from Kafka topic.
     */
    private static Dataset<Row> createKafkaStream(SparkSession spark, String kafkaTopic, String kafkaServers) {
        logger.info("\n🔄 Creating Kafka stream from topic: {}", kafkaTopic);
        logger.info("   Kafka servers: {}", kafkaServers);
        
        // Read from Kafka
        Dataset<Row> kafkaDF = spark
            .readStream()
            .format("kafka")
            .option("kafka.bootstrap.servers", kafkaServers)
            .option("subscribe", kafkaTopic)
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .load();
        
        // Parse JSON messages
        StructType schema = getKafkaStreamSchema();
        
        Dataset<Row> parsedDF = kafkaDF
            .select(
                col("key").cast("string"),
                from_json(col("value").cast("string"), schema).alias("data"),
                col("topic"),
                col("partition"),
                col("offset"),
                col("timestamp").alias("kafka_timestamp")
            )
            .select(
                col("key"),
                col("data.*"),
                col("topic"),
                col("partition"),
                col("offset"),
                col("kafka_timestamp")
            )
            .withColumn("processed_timestamp", current_timestamp())
            .withColumn("event_timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))
            .withColumn("total_amount", col("price").multiply(col("quantity")))
            .filter(col("event_timestamp").isNotNull());
        
        logger.info("✅ Kafka stream created and parsed");
        return parsedDF;
    }
    
    /**
     * Create real-time analytics queries.
     */
    private static void setupRealTimeAnalytics(Dataset<Row> streamDF, String outputPath, int duration) {
        logger.info("\n🔄 Setting up real-time analytics...");
        
        try {
            // 1. Basic event counts per minute
            logger.info("   Creating minute-by-minute event counts...");
            Dataset<Row> minuteCounts = streamDF
                .withWatermark("event_timestamp", "2 minutes")
                .groupBy(
                    window(col("event_timestamp"), "1 minute"),
                    col("event_type")
                )
                .agg(
                    count("*").alias("event_count"),
                    sum("total_amount").alias("total_revenue")
                );
            
            // Console output for monitoring
            StreamingQuery consoleQuery1 = minuteCounts
                .writeStream()
                .outputMode("update")
                .format("console")
                .option("truncate", "false")
                .option("numRows", 20)
                .trigger(Trigger.ProcessingTime("30 seconds"))
                .start();
            
            // 2. High-value transaction alerts
            logger.info("   Creating high-value transaction alerts...");
            Dataset<Row> highValueAlerts = streamDF
                .filter(col("total_amount").gt(500))
                .select(
                    col("event_id"),
                    col("user_id"),
                    col("total_amount"),
                    col("category"),
                    col("event_timestamp"),
                    lit("HIGH_VALUE_TRANSACTION").alias("alert_type")
                );
            
            StreamingQuery consoleQuery2 = highValueAlerts
                .writeStream()
                .outputMode("append")
                .format("console")
                .option("truncate", "false")
                .trigger(Trigger.ProcessingTime("10 seconds"))
                .start();
            
            // 3. Category revenue tracking (5-minute windows)
            logger.info("   Creating revenue tracking by category...");
            Dataset<Row> categoryRevenue = streamDF
                .withWatermark("event_timestamp", "5 minutes")
                .groupBy(
                    window(col("event_timestamp"), "5 minutes", "1 minute"),
                    col("category")
                )
                .agg(
                    sum("total_amount").alias("revenue"),
                    count("*").alias("order_count"),
                    avg("total_amount").alias("avg_order_value")
                );
            
            // File output for persistence
            StreamingQuery fileQuery = categoryRevenue
                .writeStream()
                .outputMode("update")
                .format("parquet")
                .option("path", outputPath + "/category_revenue")
                .option("checkpointLocation", outputPath + "/checkpoints/category_revenue")
                .trigger(Trigger.ProcessingTime("1 minute"))
                .start();
            
            // 4. Memory sink for testing
            logger.info("   Setting up memory sink for testing...");
            StreamingQuery memoryQuery = minuteCounts
                .writeStream()
                .outputMode("update")
                .format("memory")
                .queryName("event_counts_table")
                .trigger(Trigger.ProcessingTime("30 seconds"))
                .start();
            
            logger.info("✅ {} streaming queries started", 4);
            
            // Monitor queries for the specified duration
            monitorStreamingProgress(spark, duration, consoleQuery1, consoleQuery2, fileQuery, memoryQuery);
            
        } catch (Exception e) {
            logger.error("Error setting up real-time analytics: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }
    
    /**
     * Monitor streaming query progress and metrics.
     */
    private static void monitorStreamingProgress(SparkSession spark, int duration, StreamingQuery... queries) {
        logger.info("\n📊 Monitoring streaming queries for {} seconds...", duration);
        
        long startTime = System.currentTimeMillis();
        long endTime = startTime + (duration * 1000L);
        
        try {
            while (System.currentTimeMillis() < endTime) {
                long currentTime = System.currentTimeMillis();
                long elapsed = (currentTime - startTime) / 1000;
                long remaining = (endTime - currentTime) / 1000;
                
                logger.info("\n⏱️  Elapsed: {}s | Remaining: {}s", elapsed, remaining);
                
                // Check query status
                int activeCount = 0;
                for (int i = 0; i < queries.length; i++) {
                    StreamingQuery query = queries[i];
                    if (query.isActive()) {
                        activeCount++;
                        try {
                            if (query.lastProgress() != null) {
                                String batchId = String.valueOf(query.lastProgress().batchId());
                                double inputRows = query.lastProgress().inputRowsPerSecond();
                                double processedRows = query.lastProgress().processedRowsPerSecond();
                                logger.info("   Query {}: Batch {}, Input: {:.1f} rows/s, Processed: {:.1f} rows/s", 
                                    i + 1, batchId, inputRows, processedRows);
                            }
                        } catch (Exception e) {
                            logger.debug("Could not get progress for query {}: {}", i + 1, e.getMessage());
                        }
                    } else {
                        logger.info("   Query {}: ❌ Stopped", i + 1);
                    }
                }
                
                logger.info("   Active Queries: {}/{}", activeCount, queries.length);
                
                // Show memory table contents (if available)
                try {
                    Dataset<Row> memoryData = spark.sql("SELECT * FROM event_counts_table");
                    long recordCount = memoryData.count();
                    if (recordCount > 0) {
                        logger.info("   Memory Table Records: {}", recordCount);
                    }
                } catch (Exception e) {
                    // Memory table might not be available yet
                }
                
                // Wait before next check
                Thread.sleep(15000);
            }
            
        } catch (InterruptedException e) {
            logger.info("\n⚠️  Monitoring interrupted by user");
        } catch (Exception e) {
            logger.error("Error during monitoring: {}", e.getMessage());
        }
        
        // Stop all queries
        logger.info("\n🔄 Stopping streaming queries...");
        for (int i = 0; i < queries.length; i++) {
            StreamingQuery query = queries[i];
            if (query.isActive()) {
                try {
                    logger.info("   Stopping query {}...", i + 1);
                    query.stop();
                } catch (Exception e) {
                    logger.warn("Error stopping query {}: {}", i + 1, e.getMessage());
                }
            }
        }
        
        // Wait for graceful shutdown
        try {
            logger.info("   Waiting for graceful shutdown...");
            Thread.sleep(5000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        logger.info("✅ All streaming queries stopped");
    }
    
    /**
     * Generate sample data instruction for testing.
     */
    private static void generateSampleKafkaData(String kafkaTopic) {
        logger.info("\n🔄 To test streaming, send JSON messages to Kafka topic: {}", kafkaTopic);
        logger.info("   Example message format:");
        
        String exampleMessage = "{\n" +
            "  \"event_id\": \"evt_12345\",\n" +
            "  \"user_id\": \"user_123\",\n" +
            "  \"event_type\": \"purchase\",\n" +
            "  \"product_id\": \"prod_456\",\n" +
            "  \"category\": \"electronics\",\n" +
            "  \"price\": 299.99,\n" +
            "  \"quantity\": 1,\n" +
            "  \"session_id\": \"session_789\",\n" +
            "  \"timestamp\": \"" + SparkCommon.getCurrentTimestamp() + "\",\n" +
            "  \"metadata\": {\n" +
            "    \"source\": \"web\",\n" +
            "    \"version\": \"1.0\",\n" +
            "    \"user_agent\": \"Mozilla/5.0\",\n" +
            "    \"ip_address\": \"192.168.1.100\"\n" +
            "  }\n" +
            "}";
        
        logger.info(exampleMessage);
        
        logger.info("\n   Send messages using kafka-console-producer:");
        logger.info("   echo '{}' | kafka-console-producer.sh --topic {} --bootstrap-server <kafka-servers>", 
            exampleMessage.replace("\n", "").replace("  ", ""), kafkaTopic);
    }
    
    /**
     * Main streaming workflow.
     */
    public static void main(String[] args) {
        // Parse arguments
        Map<String, String> parsedArgs = SparkCommon.parseArgs(args);
        
        if (parsedArgs.containsKey("help")) {
            SparkCommon.printUsage("Streaming");
            return;
        }
        
        String kafkaTopic = parsedArgs.get("kafka-topic");
        int duration = Integer.parseInt(parsedArgs.get("duration"));
        String outputPath = parsedArgs.get("output-path");
        
        logger.info("🚀 Starting Spark Structured Streaming Example");
        logger.info("   Kafka topic: {}", kafkaTopic);
        logger.info("   Duration: {} seconds", duration);
        logger.info("   Output path: {}", outputPath);
        logger.info("   Master: {}", parsedArgs.get("master"));
        
        // Create Spark session with streaming configuration
        SparkCommon.SparkConfig config = SparkCommon.createConfigFromArgs(parsedArgs);
        config.setAppName(parsedArgs.get("app-name") + "_Streaming");
        
        SparkSession spark = SparkCommon.createSparkSession(config);
        
        // Configure streaming settings
        spark.conf().set("spark.sql.streaming.metricsEnabled", "true");
        spark.conf().set("spark.sql.streaming.ui.enabled", "true");
        
        // Setup checkpoint directory
        SparkCommon.setupKafkaCheckpoint(spark, config, "streaming_example");
        
        try {
            SparkCommon.executeWithErrorHandling(() -> {
                // Create Kafka stream
                Dataset<Row> streamDF = createKafkaStream(spark, kafkaTopic, config.getKafkaServers());
                
                // Setup analytics queries and monitor
                setupRealTimeAnalytics(streamDF, outputPath, duration);
                
                // Generate sample data instruction
                generateSampleKafkaData(kafkaTopic);
                
            }, "Streaming Pipeline");
            
            logger.info("\n✅ Streaming example completed!");
            logger.info("   Processed streams for {} seconds", duration);
            logger.info("   Results available in: {}", outputPath);
            logger.info("   Spark Streaming UI: http://192.168.1.184:4040");
            
        } catch (Exception e) {
            logger.error("Streaming error: {}", e.getMessage());
            throw new RuntimeException(e);
        } finally {
            SparkCommon.cleanupSession(spark);
        }
    }
}
