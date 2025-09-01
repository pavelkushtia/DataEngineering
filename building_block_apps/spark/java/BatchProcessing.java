import org.apache.spark.sql.SparkSession;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SaveMode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

import static org.apache.spark.sql.functions.*;

/**
 * Spark Batch Processing Examples - Building Block Application
 * 
 * This class demonstrates common batch processing patterns with Apache Spark in Java:
 * - Data loading and transformation
 * - Aggregations and analytics
 * - Data quality checks
 * - Performance optimization techniques
 * - Multiple output formats
 * 
 * Usage:
 *   bazel run //spark/java:BatchProcessing -- --records 50000 --output-path /tmp/batch-results
 * 
 * Examples:
 *   # Basic batch processing
 *   bazel run //spark/java:BatchProcessing
 *   
 *   # Large dataset processing
 *   bazel run //spark/java:BatchProcessing -- --records 1000000
 *   
 *   # Custom output location
 *   bazel run //spark/java:BatchProcessing -- --output-path /tmp/my-results
 */
public class BatchProcessing {
    
    private static final Logger logger = LoggerFactory.getLogger(BatchProcessing.class);
    
    /**
     * Load sample data and perform basic cleaning operations.
     */
    private static Dataset<Row> loadAndCleanData(SparkSession spark, int numRecords) {
        logger.info("\n🔄 Step 1: Loading and cleaning data...");
        
        // Generate sample data
        Dataset<Row> df = SparkCommon.generateSampleData(spark, numRecords);
        
        // Data cleaning operations
        Dataset<Row> cleanedDf = df
            .filter(col("price").gt(0))
            .filter(col("quantity").gt(0))
            .withColumn("category", upper(trim(col("category"))))
            .withColumn("action", lower(trim(col("action"))))
            .withColumn("total_amount", col("price").multiply(col("quantity")))
            .withColumn("date", date_format(col("timestamp"), "yyyy-MM-dd"))
            .withColumn("hour", hour(col("timestamp")))
            .dropDuplicates();
        
        logger.info("   Original records: {}", df.count());
        logger.info("   After cleaning: {}", cleanedDf.count());
        logger.info("   Records removed: {}", df.count() - cleanedDf.count());
        
        return cleanedDf;
    }
    
    /**
     * Perform various aggregation operations on the data.
     */
    private static void performAggregations(Dataset<Row> df, String outputPath) {
        logger.info("\n🔄 Step 2: Performing aggregations...");
        
        // Basic statistics
        logger.info("   Computing basic statistics...");
        Dataset<Row> statsDF = df.agg(
            count("*").alias("total_records"),
            sum("total_amount").alias("total_revenue"),
            avg("total_amount").alias("avg_order_value"),
            max("total_amount").alias("max_order_value"),
            min("total_amount").alias("min_order_value")
        );
        
        logger.info("   Basic Statistics:");
        statsDF.show();
        
        // Revenue by category
        logger.info("   Computing revenue by category...");
        Dataset<Row> categoryRevenue = df.groupBy("category")
            .agg(
                sum("total_amount").alias("revenue"),
                count("*").alias("order_count"),
                avg("total_amount").alias("avg_order_value")
            )
            .orderBy(desc("revenue"));
        
        logger.info("   Revenue by Category:");
        categoryRevenue.show();
        
        // Daily trends
        logger.info("   Computing daily trends...");
        Dataset<Row> dailyTrends = df.groupBy("date")
            .agg(
                sum("total_amount").alias("daily_revenue"),
                count("*").alias("daily_orders"),
                countDistinct("user_id").alias("daily_users")
            )
            .orderBy(desc("date"));
        
        logger.info("   Daily Trends:");
        dailyTrends.show(10);
        
        // Save aggregation results
        try {
            categoryRevenue.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/category_revenue");
                
            dailyTrends.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/daily_trends");
                
            logger.info("   ✅ Aggregation results saved to: {}", outputPath);
        } catch (Exception e) {
            logger.warn("   ⚠️  Error saving aggregation results: {}", e.getMessage());
        }
    }
    
    /**
     * Demonstrate window functions for advanced analytics.
     */
    private static Dataset<Row> performWindowOperations(Dataset<Row> df) {
        logger.info("\n🔄 Step 3: Performing window operations...");
        
        // Define window specifications
        org.apache.spark.sql.expressions.WindowSpec userWindow = 
            org.apache.spark.sql.expressions.Window
                .partitionBy("user_id")
                .orderBy("timestamp");
        
        org.apache.spark.sql.expressions.WindowSpec categoryWindow = 
            org.apache.spark.sql.expressions.Window
                .partitionBy("category")
                .orderBy(desc("total_amount"));
        
        // Add window function columns
        Dataset<Row> windowedDF = df
            .withColumn("user_order_number", row_number().over(userWindow))
            .withColumn("previous_purchase", lag(col("total_amount"), 1).over(userWindow))
            .withColumn("category_rank", rank().over(categoryWindow))
            .withColumn("is_first_purchase", 
                when(col("user_order_number").equalTo(1), true).otherwise(false));
        
        logger.info("   Added window function columns:");
        logger.info("     - user_order_number: Sequential order number per user");
        logger.info("     - previous_purchase: Previous purchase amount");
        logger.info("     - category_rank: Rank within category by order value");
        logger.info("     - is_first_purchase: Boolean flag for first-time customers");
        
        return windowedDF;
    }
    
    /**
     * Perform data quality checks.
     */
    private static void dataQualityChecks(Dataset<Row> df) {
        logger.info("\n🔄 Step 4: Performing data quality checks...");
        
        long totalRecords = df.count();
        
        // Null value checks
        logger.info("   Checking for null values...");
        for (String column : df.columns()) {
            long nullCount = df.filter(col(column).isNull()).count();
            double nullPercentage = totalRecords > 0 ? (double) nullCount / totalRecords * 100 : 0;
            if (nullPercentage > 0) {
                logger.info("     {}: {} nulls ({:.2f}%)", column, nullCount, nullPercentage);
            }
        }
        
        // Duplicate analysis
        logger.info("   Checking for duplicates...");
        long uniqueRecords = df.dropDuplicates().count();
        long duplicateCount = totalRecords - uniqueRecords;
        double duplicatePercentage = totalRecords > 0 ? (double) duplicateCount / totalRecords * 100 : 0;
        
        logger.info("     Total records: {}", totalRecords);
        logger.info("     Unique records: {}", uniqueRecords);
        logger.info("     Duplicates: {} ({:.2f}%)", duplicateCount, duplicatePercentage);
        
        // Business rule validations
        logger.info("   Validating business rules...");
        long negativePrices = df.filter(col("price").leq(0)).count();
        long negativeQuantities = df.filter(col("quantity").leq(0)).count();
        long futureTimestamps = df.filter(col("timestamp").gt(current_timestamp())).count();
        
        logger.info("     Negative prices: {}", negativePrices);
        logger.info("     Negative quantities: {}", negativeQuantities);
        logger.info("     Future timestamps: {}", futureTimestamps);
        
        // Data distribution analysis
        logger.info("   Analyzing data distributions...");
        logger.info("     Category distribution:");
        df.groupBy("category").count().orderBy(desc("count")).show(10);
        
        logger.info("     Action distribution:");
        df.groupBy("action").count().orderBy(desc("count")).show(10);
    }
    
    /**
     * Save results in multiple formats.
     */
    private static void saveResults(Dataset<Row> windowedDF, String outputPath) {
        logger.info("\n🔄 Step 5: Saving results to {}...", outputPath);
        
        try {
            // Save windowed data sample as Parquet
            logger.info("   Saving windowed data sample...");
            windowedDF.sample(0.1)
                .coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .parquet(outputPath + "/windowed_sample");
            
            // Save full dataset partitioned by category and date
            logger.info("   Saving full dataset...");
            windowedDF.write()
                .mode(SaveMode.Overwrite)
                .partitionBy("category", "date")
                .parquet(outputPath + "/full_dataset");
            
            logger.info("✅ Results saved to: {}", outputPath);
            logger.info("   - Parquet files: windowed_sample, full_dataset (partitioned)");
            
        } catch (Exception e) {
            logger.warn("⚠️  Error saving results: {}", e.getMessage());
            logger.warn("   Results computed successfully but not saved to disk");
        }
    }
    
    /**
     * Print a comprehensive summary of results.
     */
    private static void printResultsSummary(Dataset<Row> df) {
        logger.info("\n" + "=".repeat(60));
        logger.info("📊 BATCH PROCESSING RESULTS SUMMARY");
        logger.info("=".repeat(60));
        
        try {
            // Basic statistics
            Row stats = df.agg(
                count("*").alias("total_records"),
                sum("total_amount").alias("total_revenue"),
                avg("total_amount").alias("avg_order_value"),
                max("total_amount").alias("max_order_value"),
                min("total_amount").alias("min_order_value")
            ).first();
            
            logger.info("\n💰 REVENUE SUMMARY:");
            logger.info("   Total Records: {}", stats.getLong(0));
            logger.info("   Total Revenue: ${:.2f}", stats.getDouble(1));
            logger.info("   Average Order Value: ${:.2f}", stats.getDouble(2));
            logger.info("   Max Order Value: ${:.2f}", stats.getDouble(3));
            logger.info("   Min Order Value: ${:.2f}", stats.getDouble(4));
            
            // Top categories
            logger.info("\n🏆 TOP CATEGORIES BY REVENUE:");
            Dataset<Row> topCategories = df.groupBy("category")
                .agg(sum("total_amount").alias("revenue"), count("*").alias("order_count"))
                .orderBy(desc("revenue"))
                .limit(3);
            
            Row[] categoryRows = (Row[]) topCategories.collect();
            for (int i = 0; i < categoryRows.length; i++) {
                Row row = categoryRows[i];
                logger.info("   {}. {}: ${:.2f} ({} orders)", 
                    i + 1, row.getString(0), row.getDouble(1), row.getLong(2));
            }
            
        } catch (Exception e) {
            logger.warn("Error generating summary: {}", e.getMessage());
        }
        
        logger.info("\n" + "=".repeat(60));
    }
    
    /**
     * Main batch processing workflow.
     */
    public static void main(String[] args) {
        // Parse arguments
        Map<String, String> parsedArgs = SparkCommon.parseArgs(args);
        
        if (parsedArgs.containsKey("help")) {
            SparkCommon.printUsage("BatchProcessing");
            return;
        }
        
        int records = Integer.parseInt(parsedArgs.get("records"));
        String outputPath = parsedArgs.get("output-path");
        
        logger.info("🚀 Starting Spark Batch Processing Example");
        logger.info("   Records to process: {}", records);
        logger.info("   Output path: {}", outputPath);
        logger.info("   Master: {}", parsedArgs.get("master"));
        
        // Create Spark session
        SparkCommon.SparkConfig config = SparkCommon.createConfigFromArgs(parsedArgs);
        config.setAppName(parsedArgs.get("app-name") + "_BatchProcessing");
        
        SparkSession spark = SparkCommon.createSparkSession(config);
        
        try {
            long startTime = System.currentTimeMillis();
            
            // Execute batch processing pipeline
            SparkCommon.executeWithErrorHandling(() -> {
                // Step 1: Load and clean data
                Dataset<Row> cleanedDF = loadAndCleanData(spark, records);
                SparkCommon.printDatasetSummary(cleanedDF, "Cleaned Dataset", records <= 10000);
                
                // Step 2: Perform aggregations
                performAggregations(cleanedDF, outputPath);
                
                // Step 3: Window operations
                Dataset<Row> windowedDF = performWindowOperations(cleanedDF);
                
                // Step 4: Data quality checks
                dataQualityChecks(windowedDF);
                
                // Step 5: Save results
                saveResults(windowedDF, outputPath);
                
                // Print summary
                printResultsSummary(windowedDF);
                
            }, "Batch Processing Pipeline");
            
            // Monitor performance
            SparkCommon.monitorJobProgress(spark, "Batch Processing");
            
            long endTime = System.currentTimeMillis();
            double processingTime = (endTime - startTime) / 1000.0;
            
            logger.info("\n⏱️  Total Processing Time: {:.2f} seconds", processingTime);
            logger.info("   Records per second: {:.0f}", records / processingTime);
            
            logger.info("\n✅ Batch processing completed successfully!");
            logger.info("   Processed {} records in {:.2f} seconds", records, processingTime);
            logger.info("   Results saved to: {}", outputPath);
            
        } finally {
            SparkCommon.cleanupSession(spark);
        }
    }
}
