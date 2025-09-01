import org.apache.spark.sql.SparkSession;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SaveMode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * Spark SQL Examples - Building Block Application
 * 
 * This class demonstrates advanced SQL capabilities with Apache Spark in Java:
 * - Complex analytical queries with window functions
 * - Data transformation and ETL operations
 * - Performance optimization techniques
 * - Advanced SQL features (CTEs, UDFs, etc.)
 * 
 * Usage:
 *   bazel run //spark/java:SqlQueries -- --records 100000
 * 
 * Examples:
 *   # Basic SQL analytics
 *   bazel run //spark/java:SqlQueries
 *   
 *   # Large dataset analysis
 *   bazel run //spark/java:SqlQueries -- --records 1000000
 */
public class SqlQueries {
    
    private static final Logger logger = LoggerFactory.getLogger(SqlQueries.class);
    
    /**
     * Setup sample tables for SQL demonstrations.
     */
    private static void setupSampleTables(SparkSession spark, int numRecords) {
        logger.info("\n🔄 Setting up sample tables with {} records...", numRecords);
        
        // Generate main dataset
        Dataset<Row> df = SparkCommon.generateSampleData(spark, numRecords);
        
        // Create temporary views for SQL queries
        df.createOrReplaceTempView("sales");
        logger.info("   ✅ Created 'sales' table");
        
        // Show table schema
        logger.info("\n📋 Sales Table Schema:");
        spark.sql("DESCRIBE sales").show();
    }
    
    /**
     * Execute basic SQL queries for analytics.
     */
    private static void executeBasicSQLQueries(SparkSession spark, String outputPath) {
        logger.info("\n🔄 Executing basic SQL queries...");
        
        // 1. Sales summary by category
        logger.info("   1. Sales summary by category...");
        Dataset<Row> salesSummary = spark.sql(
            "SELECT " +
            "    category, " +
            "    COUNT(*) as order_count, " +
            "    SUM(price * quantity) as total_revenue, " +
            "    AVG(price * quantity) as avg_order_value, " +
            "    MIN(price * quantity) as min_order_value, " +
            "    MAX(price * quantity) as max_order_value " +
            "FROM sales " +
            "WHERE price > 0 AND quantity > 0 " +
            "GROUP BY category " +
            "ORDER BY total_revenue DESC"
        );
        
        logger.info("   Sales Summary by Category:");
        salesSummary.show();
        
        // 2. Daily trends
        logger.info("   2. Daily sales trends...");
        Dataset<Row> dailyTrends = spark.sql(
            "SELECT " +
            "    DATE(timestamp) as sale_date, " +
            "    COUNT(*) as daily_orders, " +
            "    SUM(price * quantity) as daily_revenue, " +
            "    COUNT(DISTINCT user_id) as unique_customers, " +
            "    AVG(price * quantity) as avg_order_value " +
            "FROM sales " +
            "GROUP BY DATE(timestamp) " +
            "ORDER BY sale_date DESC " +
            "LIMIT 10"
        );
        
        logger.info("   Daily Trends:");
        dailyTrends.show();
        
        // 3. Top users by spending
        logger.info("   3. Top users by spending...");
        Dataset<Row> topUsers = spark.sql(
            "SELECT " +
            "    user_id, " +
            "    COUNT(*) as total_orders, " +
            "    SUM(price * quantity) as total_spent, " +
            "    AVG(price * quantity) as avg_order_value " +
            "FROM sales " +
            "GROUP BY user_id " +
            "ORDER BY total_spent DESC " +
            "LIMIT 10"
        );
        
        logger.info("   Top Users:");
        topUsers.show();
        
        // Save results
        try {
            salesSummary.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/sales_summary");
                
            dailyTrends.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/daily_trends");
                
            topUsers.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/top_users");
                
            logger.info("   ✅ Basic query results saved to: {}", outputPath);
        } catch (Exception e) {
            logger.warn("   ⚠️  Error saving basic query results: {}", e.getMessage());
        }
    }
    
    /**
     * Execute advanced SQL queries with window functions and CTEs.
     */
    private static void executeAdvancedSQLQueries(SparkSession spark, String outputPath) {
        logger.info("\n🔄 Executing advanced SQL queries...");
        
        // 1. Running totals with window functions
        logger.info("   1. Running totals and rankings...");
        Dataset<Row> runningAnalytics = spark.sql(
            "SELECT " +
            "    user_id, " +
            "    timestamp, " +
            "    price * quantity as order_value, " +
            "    SUM(price * quantity) OVER (" +
            "        PARTITION BY user_id " +
            "        ORDER BY timestamp " +
            "        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW" +
            "    ) as running_total, " +
            "    ROW_NUMBER() OVER (" +
            "        PARTITION BY user_id " +
            "        ORDER BY timestamp" +
            "    ) as order_sequence, " +
            "    LAG(price * quantity, 1) OVER (" +
            "        PARTITION BY user_id " +
            "        ORDER BY timestamp" +
            "    ) as previous_order_value, " +
            "    RANK() OVER (" +
            "        PARTITION BY DATE(timestamp) " +
            "        ORDER BY price * quantity DESC" +
            "    ) as daily_rank " +
            "FROM sales " +
            "WHERE user_id IN (" +
            "    SELECT user_id " +
            "    FROM sales " +
            "    GROUP BY user_id " +
            "    HAVING COUNT(*) >= 3" +
            ") " +
            "ORDER BY user_id, timestamp"
        );
        
        logger.info("   Running Analytics (sample):");
        runningAnalytics.show(20);
        
        // 2. Statistical analysis with percentiles
        logger.info("   2. Statistical analysis...");
        Dataset<Row> statisticalAnalysis = spark.sql(
            "SELECT " +
            "    category, " +
            "    COUNT(*) as sample_size, " +
            "    AVG(price * quantity) as mean_value, " +
            "    STDDEV(price * quantity) as std_deviation, " +
            "    PERCENTILE_APPROX(price * quantity, 0.5) as median, " +
            "    PERCENTILE_APPROX(price * quantity, 0.9) as p90, " +
            "    PERCENTILE_APPROX(price * quantity, 0.95) as p95 " +
            "FROM sales " +
            "GROUP BY category " +
            "ORDER BY mean_value DESC"
        );
        
        logger.info("   Statistical Analysis:");
        statisticalAnalysis.show();
        
        // 3. Customer behavior analysis with CTEs
        logger.info("   3. Customer behavior analysis...");
        Dataset<Row> customerBehavior = spark.sql(
            "WITH user_stats AS (" +
            "    SELECT " +
            "        user_id, " +
            "        COUNT(*) as total_orders, " +
            "        SUM(price * quantity) as total_spent, " +
            "        AVG(price * quantity) as avg_order_value, " +
            "        COUNT(DISTINCT category) as categories_purchased, " +
            "        MIN(timestamp) as first_purchase, " +
            "        MAX(timestamp) as last_purchase " +
            "    FROM sales " +
            "    GROUP BY user_id" +
            "), " +
            "customer_segments AS (" +
            "    SELECT " +
            "        user_id, " +
            "        total_orders, " +
            "        total_spent, " +
            "        avg_order_value, " +
            "        categories_purchased, " +
            "        CASE " +
            "            WHEN total_spent >= 1000 THEN 'High Value' " +
            "            WHEN total_spent >= 500 THEN 'Medium Value' " +
            "            ELSE 'Low Value' " +
            "        END as customer_tier, " +
            "        CASE " +
            "            WHEN total_orders >= 10 THEN 'Frequent' " +
            "            WHEN total_orders >= 5 THEN 'Regular' " +
            "            ELSE 'Occasional' " +
            "        END as purchase_frequency " +
            "    FROM user_stats" +
            ") " +
            "SELECT " +
            "    customer_tier, " +
            "    purchase_frequency, " +
            "    COUNT(*) as customer_count, " +
            "    AVG(total_spent) as avg_spending, " +
            "    AVG(total_orders) as avg_orders, " +
            "    AVG(categories_purchased) as avg_categories " +
            "FROM customer_segments " +
            "GROUP BY customer_tier, purchase_frequency " +
            "ORDER BY avg_spending DESC"
        );
        
        logger.info("   Customer Behavior Analysis:");
        customerBehavior.show();
        
        // Save advanced results
        try {
            runningAnalytics.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .parquet(outputPath + "/running_analytics");
                
            statisticalAnalysis.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/statistical_analysis");
                
            customerBehavior.coalesce(1)
                .write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/customer_behavior");
                
            logger.info("   ✅ Advanced query results saved to: {}", outputPath);
        } catch (Exception e) {
            logger.warn("   ⚠️  Error saving advanced query results: {}", e.getMessage());
        }
    }
    
    /**
     * Print a summary of SQL query results.
     */
    private static void printSQLSummary(SparkSession spark) {
        logger.info("\n" + "=".repeat(60));
        logger.info("📊 SQL QUERIES RESULTS SUMMARY");
        logger.info("=".repeat(60));
        
        try {
            // Overall statistics
            Row overallStats = spark.sql(
                "SELECT " +
                "    COUNT(*) as total_records, " +
                "    COUNT(DISTINCT user_id) as unique_users, " +
                "    COUNT(DISTINCT category) as categories, " +
                "    SUM(price * quantity) as total_revenue " +
                "FROM sales"
            ).first();
            
            logger.info("\n📈 OVERALL STATISTICS:");
            logger.info("   Total Records: {}", overallStats.getLong(0));
            logger.info("   Unique Users: {}", overallStats.getLong(1));
            logger.info("   Categories: {}", overallStats.getLong(2));
            logger.info("   Total Revenue: ${:.2f}", overallStats.getDouble(3));
            
            // Top category
            Row topCategory = spark.sql(
                "SELECT category, SUM(price * quantity) as revenue " +
                "FROM sales GROUP BY category " +
                "ORDER BY revenue DESC LIMIT 1"
            ).first();
            
            logger.info("\n🏆 TOP PERFORMING CATEGORY:");
            logger.info("   {}: ${:.2f}", topCategory.getString(0), topCategory.getDouble(1));
            
        } catch (Exception e) {
            logger.warn("Error generating SQL summary: {}", e.getMessage());
        }
        
        logger.info("\n" + "=".repeat(60));
    }
    
    /**
     * Main SQL workflow.
     */
    public static void main(String[] args) {
        // Parse arguments
        Map<String, String> parsedArgs = SparkCommon.parseArgs(args);
        
        if (parsedArgs.containsKey("help")) {
            SparkCommon.printUsage("SqlQueries");
            return;
        }
        
        int records = Integer.parseInt(parsedArgs.get("records"));
        String outputPath = parsedArgs.get("output-path");
        
        logger.info("🚀 Starting Spark SQL Examples");
        logger.info("   Records to process: {}", records);
        logger.info("   Output path: {}", outputPath);
        logger.info("   Master: {}", parsedArgs.get("master"));
        
        // Create Spark session
        SparkCommon.SparkConfig config = SparkCommon.createConfigFromArgs(parsedArgs);
        config.setAppName(parsedArgs.get("app-name") + "_SQL");
        
        SparkSession spark = SparkCommon.createSparkSession(config);
        
        // Enable Spark SQL optimizations
        spark.conf().set("spark.sql.adaptive.enabled", "true");
        spark.conf().set("spark.sql.adaptive.coalescePartitions.enabled", "true");
        spark.conf().set("spark.sql.adaptive.skewJoin.enabled", "true");
        spark.conf().set("spark.sql.cbo.enabled", "true");
        
        try {
            long startTime = System.currentTimeMillis();
            
            SparkCommon.executeWithErrorHandling(() -> {
                // Setup sample tables
                setupSampleTables(spark, records);
                
                // Execute SQL query categories
                executeBasicSQLQueries(spark, outputPath);
                executeAdvancedSQLQueries(spark, outputPath);
                
                // Print summary
                printSQLSummary(spark);
                
            }, "SQL Queries");
            
            // Monitor performance
            SparkCommon.monitorJobProgress(spark, "SQL Queries");
            
            long endTime = System.currentTimeMillis();
            double processingTime = (endTime - startTime) / 1000.0;
            
            logger.info("\n⏱️  Total Processing Time: {:.2f} seconds", processingTime);
            logger.info("   Records processed: {}", records);
            
            logger.info("\n✅ SQL examples completed successfully!");
            logger.info("   Results saved to: {}", outputPath);
            logger.info("   Spark SQL UI: http://192.168.1.184:4040");
            
        } finally {
            SparkCommon.cleanupSession(spark);
        }
    }
}
