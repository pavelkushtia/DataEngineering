import org.apache.spark.SparkConf;
import org.apache.spark.sql.SparkSession;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.types.DataTypes;
import org.apache.spark.sql.types.StructField;
import org.apache.spark.sql.functions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Common utilities and configuration for Spark building block applications in Java.
 * 
 * This class provides:
 * - Spark session creation with optimized settings
 * - Common data schemas and sample data generation
 * - Utility functions for performance monitoring
 * - Error handling patterns
 * - Configuration management
 */
public class SparkCommon implements Serializable {
    
    private static final Logger logger = LoggerFactory.getLogger(SparkCommon.class);
    private static final String DEFAULT_MASTER = "spark://192.168.1.184:7077";
    private static final String DEFAULT_APP_NAME = "SparkBuildingBlock";
    
    /**
     * Configuration class for Spark applications.
     */
    public static class SparkConfig implements Serializable {
        private String appName;
        private String master;
        private String executorMemory;
        private String executorCores;
        private String driverMemory;
        private String kafkaServers;
        private String checkpointDir;
        private String warehouseDir;
        
        public SparkConfig() {
            this.appName = DEFAULT_APP_NAME;
            this.master = DEFAULT_MASTER;
            this.executorMemory = "2g";
            this.executorCores = "2";
            this.driverMemory = "1g";
            this.kafkaServers = "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092";
            this.checkpointDir = "/tmp/spark-checkpoints";
            this.warehouseDir = "/home/spark/spark/warehouse";
        }
        
        // Getters and setters
        public String getAppName() { return appName; }
        public void setAppName(String appName) { this.appName = appName; }
        
        public String getMaster() { return master; }
        public void setMaster(String master) { this.master = master; }
        
        public String getExecutorMemory() { return executorMemory; }
        public void setExecutorMemory(String executorMemory) { this.executorMemory = executorMemory; }
        
        public String getExecutorCores() { return executorCores; }
        public void setExecutorCores(String executorCores) { this.executorCores = executorCores; }
        
        public String getDriverMemory() { return driverMemory; }
        public void setDriverMemory(String driverMemory) { this.driverMemory = driverMemory; }
        
        public String getKafkaServers() { return kafkaServers; }
        public void setKafkaServers(String kafkaServers) { this.kafkaServers = kafkaServers; }
        
        public String getCheckpointDir() { return checkpointDir; }
        public void setCheckpointDir(String checkpointDir) { this.checkpointDir = checkpointDir; }
        
        public String getWarehouseDir() { return warehouseDir; }
        public void setWarehouseDir(String warehouseDir) { this.warehouseDir = warehouseDir; }
    }
    
    /**
     * Create a Spark session with optimized configuration.
     * 
     * @param config SparkConfig object with application settings
     * @return Configured SparkSession
     */
    public static SparkSession createSparkSession(SparkConfig config) {
        logger.info("Creating Spark session: {}", config.getAppName());
        
        SparkConf sparkConf = new SparkConf()
            .setAppName(config.getAppName())
            .setMaster(config.getMaster())
            .set("spark.executor.memory", config.getExecutorMemory())
            .set("spark.executor.cores", config.getExecutorCores())
            .set("spark.driver.memory", config.getDriverMemory())
            .set("spark.sql.warehouse.dir", config.getWarehouseDir())
            .set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .set("spark.sql.adaptive.enabled", "true")
            .set("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .set("spark.sql.adaptive.skewJoin.enabled", "true")
            .set("spark.dynamicAllocation.enabled", "false");
        
        // Add Kafka dependencies if available
        try {
            sparkConf.set("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6");
        } catch (Exception e) {
            logger.warn("Kafka package not available, streaming examples may fail: {}", e.getMessage());
        }
        
        SparkSession spark = SparkSession.builder()
            .config(sparkConf)
            .getOrCreate();
        
        spark.sparkContext().setLogLevel("WARN");
        
        logger.info("✅ Spark session created successfully");
        logger.info("   Master: {}", config.getMaster());
        logger.info("   Executor Memory: {}", config.getExecutorMemory());
        logger.info("   Executor Cores: {}", config.getExecutorCores());
        
        return spark;
    }
    
    /**
     * Define a common schema for sample data used across examples.
     * 
     * @return StructType schema for sample e-commerce data
     */
    public static StructType getSampleDataSchema() {
        return DataTypes.createStructType(new StructField[] {
            DataTypes.createStructField("user_id", DataTypes.StringType, true),
            DataTypes.createStructField("product_id", DataTypes.StringType, true),
            DataTypes.createStructField("category", DataTypes.StringType, true),
            DataTypes.createStructField("action", DataTypes.StringType, true),
            DataTypes.createStructField("timestamp", DataTypes.TimestampType, true),
            DataTypes.createStructField("price", DataTypes.DoubleType, true),
            DataTypes.createStructField("quantity", DataTypes.IntegerType, true),
            DataTypes.createStructField("session_id", DataTypes.StringType, true),
            DataTypes.createStructField("is_premium", DataTypes.BooleanType, true),
            DataTypes.createStructField("region", DataTypes.StringType, true)
        });
    }
    
    /**
     * Generate sample e-commerce data for testing and examples.
     * 
     * @param spark SparkSession
     * @param numRecords Number of records to generate
     * @return Dataset with sample data
     */
    public static Dataset<Row> generateSampleData(SparkSession spark, int numRecords) {
        logger.info("🔄 Generating {} sample records...", numRecords);
        
        String[] categories = {"electronics", "clothing", "books", "home", "sports"};
        String[] actions = {"view", "add_to_cart", "purchase", "remove_from_cart"};
        String[] regions = {"US-East", "US-West", "EU", "Asia"};
        
        List<Row> data = new ArrayList<>();
        Random random = new Random();
        
        for (int i = 0; i < numRecords; i++) {
            LocalDateTime timestamp = LocalDateTime.now().minusSeconds(random.nextInt(7 * 24 * 3600));
            
            Row record = org.apache.spark.sql.RowFactory.create(
                "user_" + (random.nextInt(50000) + 1),
                "prod_" + (random.nextInt(10000) + 1),
                categories[random.nextInt(categories.length)],
                actions[random.nextInt(actions.length)],
                Timestamp.valueOf(timestamp),
                Math.round((10 + random.nextDouble() * 990) * 100.0) / 100.0,
                random.nextInt(5) + 1,
                "session_" + (random.nextInt(100000) + 1),
                random.nextBoolean(),
                regions[random.nextInt(regions.length)]
            );
            data.add(record);
            
            if ((i + 1) % 5000 == 0) {
                logger.info("   Generated {} records...", i + 1);
            }
        }
        
        Dataset<Row> df = spark.createDataFrame(data, getSampleDataSchema());
        long count = df.count();
        logger.info("✅ Generated {} records", count);
        
        return df;
    }
    
    /**
     * Print job progress and performance metrics.
     * 
     * @param spark SparkSession
     * @param jobName Name of the job for logging
     */
    public static void monitorJobProgress(SparkSession spark, String jobName) {
        logger.info("\n📊 {} Metrics:", jobName);
        logger.info("   Spark UI: http://192.168.1.184:4040");
        
        try {
            String applicationId = spark.sparkContext().applicationId();
            int defaultParallelism = spark.sparkContext().defaultParallelism();
            
            logger.info("   Application ID: {}", applicationId);
            logger.info("   Default Parallelism: {}", defaultParallelism);
            
        } catch (Exception e) {
            logger.warn("   Metrics unavailable: {}", e.getMessage());
        }
    }
    
    /**
     * Print a comprehensive summary of a Dataset.
     * 
     * @param df Dataset to summarize
     * @param name Name for the Dataset in output
     * @param showData Whether to show sample data
     */
    public static void printDatasetSummary(Dataset<Row> df, String name, boolean showData) {
        logger.info("\n📊 {} Summary:", name);
        
        try {
            long count = df.count();
            int columnCount = df.columns().length;
            
            logger.info("   Rows: {}", count);
            logger.info("   Columns: {}", columnCount);
            logger.info("   Schema:");
            
            StructType schema = df.schema();
            for (StructField field : schema.fields()) {
                logger.info("     {}: {}", field.name(), field.dataType().simpleString());
            }
            
            if (showData && count > 0) {
                logger.info("\n   Sample Data:");
                df.show(5, false);
                
                // Show basic statistics for numeric columns
                try {
                    List<String> numericCols = new ArrayList<>();
                    for (StructField field : schema.fields()) {
                        if (field.dataType().equals(DataTypes.IntegerType) || 
                            field.dataType().equals(DataTypes.DoubleType) ||
                            field.dataType().equals(DataTypes.LongType) ||
                            field.dataType().equals(DataTypes.FloatType)) {
                            numericCols.add(field.name());
                        }
                    }
                    
                    if (!numericCols.isEmpty()) {
                        logger.info("\n   Numeric Statistics:");
                        df.select(numericCols.toArray(new String[0])).describe().show();
                    }
                } catch (Exception e) {
                    logger.warn("Could not compute statistics: {}", e.getMessage());
                }
            }
        } catch (Exception e) {
            logger.error("Error generating summary for {}: {}", name, e.getMessage());
        }
    }
    
    /**
     * Setup checkpoint directory for streaming applications.
     * 
     * @param spark SparkSession
     * @param config SparkConfig
     * @param appName Application name for unique checkpoint directory
     */
    public static void setupKafkaCheckpoint(SparkSession spark, SparkConfig config, String appName) {
        String checkpointPath = config.getCheckpointDir() + "/" + appName;
        
        try {
            java.nio.file.Files.createDirectories(java.nio.file.Paths.get(checkpointPath));
            logger.info("✅ Checkpoint directory: {}", checkpointPath);
        } catch (Exception e) {
            logger.warn("⚠️  Could not create checkpoint directory: {}", e.getMessage());
            logger.warn("   Using default: /tmp/spark-checkpoints/{}", appName);
        }
    }
    
    /**
     * Parse command line arguments for Spark applications.
     * 
     * @param args Command line arguments
     * @return Map of parsed arguments with defaults
     */
    public static Map<String, String> parseArgs(String[] args) {
        Map<String, String> parsedArgs = new HashMap<>();
        
        // Set defaults
        parsedArgs.put("master", DEFAULT_MASTER);
        parsedArgs.put("app-name", DEFAULT_APP_NAME);
        parsedArgs.put("executor-memory", "2g");
        parsedArgs.put("executor-cores", "2");
        parsedArgs.put("records", "10000");
        parsedArgs.put("output-path", "/tmp/spark-output");
        parsedArgs.put("kafka-topic", "spark-demo");
        parsedArgs.put("duration", "60");
        parsedArgs.put("verbose", "false");
        
        // Parse command line arguments
        for (int i = 0; i < args.length; i++) {
            if (args[i].startsWith("--") && i + 1 < args.length) {
                String key = args[i].substring(2);
                String value = args[i + 1];
                parsedArgs.put(key, value);
                i++; // Skip the value in next iteration
            }
        }
        
        return parsedArgs;
    }
    
    /**
     * Print usage information for command line arguments.
     */
    public static void printUsage(String className) {
        System.out.println("Usage: " + className + " [OPTIONS]");
        System.out.println("Options:");
        System.out.println("  --master URL              Spark master URL (default: " + DEFAULT_MASTER + ")");
        System.out.println("  --app-name NAME           Spark application name (default: " + DEFAULT_APP_NAME + ")");
        System.out.println("  --executor-memory SIZE    Executor memory (default: 2g)");
        System.out.println("  --executor-cores NUM      Executor cores (default: 2)");
        System.out.println("  --records NUM             Number of records to process (default: 10000)");
        System.out.println("  --output-path PATH        Output path for results (default: /tmp/spark-output)");
        System.out.println("  --kafka-topic TOPIC       Kafka topic for streaming (default: spark-demo)");
        System.out.println("  --duration SECONDS        Duration for streaming jobs (default: 60)");
        System.out.println("  --verbose                 Enable verbose logging");
        System.out.println("  --help                    Show this help message");
    }
    
    /**
     * Properly clean up Spark session.
     * 
     * @param spark SparkSession to clean up
     */
    public static void cleanupSession(SparkSession spark) {
        try {
            logger.info("\n🔄 Cleaning up Spark session...");
            spark.stop();
            logger.info("✅ Spark session stopped");
        } catch (Exception e) {
            logger.warn("⚠️  Error during cleanup: {}", e.getMessage());
        }
    }
    
    /**
     * Create a SparkConfig from parsed command line arguments.
     * 
     * @param args Parsed command line arguments
     * @return SparkConfig object
     */
    public static SparkConfig createConfigFromArgs(Map<String, String> args) {
        SparkConfig config = new SparkConfig();
        config.setAppName(args.get("app-name"));
        config.setMaster(args.get("master"));
        config.setExecutorMemory(args.get("executor-memory"));
        config.setExecutorCores(args.get("executor-cores"));
        return config;
    }
    
    /**
     * Execute error handling wrapper for common operations.
     * 
     * @param operation The operation to execute
     * @param operationName Name of the operation for logging
     */
    public static void executeWithErrorHandling(Runnable operation, String operationName) {
        try {
            operation.run();
        } catch (Exception e) {
            logger.error("\n❌ Error in {}: {}", operationName, e.getMessage());
            logger.error("   Error type: {}", e.getClass().getSimpleName());
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    /**
     * Get current timestamp as formatted string.
     * 
     * @return Formatted timestamp string
     */
    public static String getCurrentTimestamp() {
        return LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
    }
    
    /**
     * Test the common utilities (main method for testing).
     */
    public static void main(String[] args) {
        System.out.println("🧪 Testing Spark common utilities...");
        
        SparkConfig config = new SparkConfig();
        config.setAppName("SparkCommonTest");
        
        SparkSession spark = createSparkSession(config);
        
        try {
            // Generate and show sample data
            Dataset<Row> df = generateSampleData(spark, 100);
            printDatasetSummary(df, "Sample Data", true);
            
            monitorJobProgress(spark, "Common Utilities Test");
            
            System.out.println("✅ Spark common utilities test completed");
            
        } finally {
            cleanupSession(spark);
        }
    }
}
