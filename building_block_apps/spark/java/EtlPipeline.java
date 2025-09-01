import org.apache.spark.sql.SparkSession;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SaveMode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

import static org.apache.spark.sql.functions.*;

/**
 * Spark ETL Pipeline Examples - Building Block Application
 * 
 * This class demonstrates comprehensive ETL (Extract, Transform, Load) pipelines in Java:
 * - Multi-source data extraction
 * - Complex data transformations and validation
 * - Multiple output formats and destinations
 * - Error handling and data quality checks
 * - Performance optimization and monitoring
 * 
 * Usage:
 *   bazel run //spark/java:EtlPipeline -- --records 50000 --output-path /tmp/etl-results
 * 
 * Examples:
 *   # Basic ETL pipeline
 *   bazel run //spark/java:EtlPipeline
 *   
 *   # Large-scale ETL with custom output
 *   bazel run //spark/java:EtlPipeline -- --records 1000000 --output-path /tmp/warehouse
 */
public class EtlPipeline {
    
    private static final Logger logger = LoggerFactory.getLogger(EtlPipeline.class);
    
    /**
     * Extract data from multiple sources (simulated).
     */
    private static Map<String, Dataset<Row>> extractDataSources(SparkSession spark, int numRecords) {
        logger.info("\n🔄 EXTRACT: Loading data from multiple sources...");
        
        // 1. Sales data (main transactional data)
        logger.info("   Loading sales transactions...");
        Dataset<Row> salesDF = SparkCommon.generateSampleData(spark, numRecords);
        
        // 2. Customer data (create synthetic customer data)
        logger.info("   Loading customer data...");
        Dataset<Row> customersDF = salesDF
            .select("user_id")
            .distinct()
            .withColumn("customer_id", regexp_replace(col("user_id"), "user_", "cust_"))
            .withColumn("full_name", concat(lit("Customer "), regexp_extract(col("user_id"), "(\\d+)", 1)))
            .withColumn("email", concat(lower(col("user_id")), lit("@example.com")))
            .withColumn("registration_date", date_sub(current_date(), 
                (col("user_id").substr(6, 10).cast("int")).mod(365)))
            .withColumn("is_active", 
                when(col("user_id").substr(6, 10).cast("int").mod(20).notEqual(0), true).otherwise(false))
            .withColumn("customer_segment", 
                when(col("user_id").substr(6, 10).cast("int").mod(3).equalTo(0), "Premium")
                .when(col("user_id").substr(6, 10).cast("int").mod(3).equalTo(1), "Standard")
                .otherwise("Basic"));
        
        // 3. Product data (create synthetic product data)
        logger.info("   Loading product catalog...");
        Dataset<Row> productsDF = salesDF
            .select("product_id", "category")
            .distinct()
            .withColumn("sku", concat(lit("SKU-"), regexp_extract(col("product_id"), "(\\d+)", 1)))
            .withColumn("name", concat(lit("Product "), regexp_extract(col("product_id"), "(\\d+)", 1)))
            .withColumn("supplier", concat(lit("Supplier_"), 
                (regexp_extract(col("product_id"), "(\\d+)", 1).cast("int")).mod(20).plus(1)))
            .withColumn("cost_price", 
                (regexp_extract(col("product_id"), "(\\d+)", 1).cast("int")).mod(500).plus(10))
            .withColumn("retail_price", col("cost_price").multiply(1.5))
            .withColumn("is_available", 
                when(col("product_id").substr(6, 10).cast("int").mod(25).notEqual(0), true).otherwise(false));
        
        logger.info("   ✅ Extracted data sources:");
        logger.info("      sales: {} records", salesDF.count());
        logger.info("      customers: {} records", customersDF.count());
        logger.info("      products: {} records", productsDF.count());
        
        return Map.of(
            "sales", salesDF,
            "customers", customersDF,
            "products", productsDF
        );
    }
    
    /**
     * Apply comprehensive data transformations.
     */
    private static Map<String, Dataset<Row>> transformData(Map<String, Dataset<Row>> sources) {
        logger.info("\n🔄 TRANSFORM: Applying data transformations...");
        
        Dataset<Row> salesDF = sources.get("sales");
        Dataset<Row> customersDF = sources.get("customers");
        Dataset<Row> productsDF = sources.get("products");
        
        // 1. Sales fact table transformations
        logger.info("   Transforming sales data...");
        Dataset<Row> salesTransformed = salesDF
            .withColumn("sale_date", date_format(col("timestamp"), "yyyy-MM-dd"))
            .withColumn("sale_hour", hour(col("timestamp")))
            .withColumn("total_amount", col("price").multiply(col("quantity")))
            .withColumn("discount_amount", 
                when(col("total_amount").gt(1000), col("total_amount").multiply(0.1))
                .when(col("total_amount").gt(500), col("total_amount").multiply(0.05))
                .otherwise(0))
            .withColumn("final_amount", col("total_amount").minus(col("discount_amount")))
            .withColumn("profit_margin", 
                when(col("category").equalTo("ELECTRONICS"), 0.15)
                .when(col("category").equalTo("CLOTHING"), 0.40)
                .when(col("category").equalTo("BOOKS"), 0.20)
                .when(col("category").equalTo("HOME"), 0.25)
                .otherwise(0.30))
            .withColumn("estimated_profit", col("final_amount").multiply(col("profit_margin")))
            .withColumn("customer_id", regexp_replace(col("user_id"), "user_", "cust_"))
            .withColumn("order_id", concat(lit("ORD-"), 
                date_format(col("timestamp"), "yyyyMMdd"), 
                lit("-"), 
                abs(hash(col("user_id"), col("timestamp")))))
            .filter(col("price").gt(0))
            .filter(col("quantity").gt(0));
        
        // 2. Customer dimension transformations
        logger.info("   Transforming customer data...");
        Dataset<Row> customersTransformed = customersDF
            .withColumn("days_since_registration", 
                datediff(current_date(), col("registration_date")))
            .withColumn("customer_age_category",
                when(col("days_since_registration").lt(30), "New")
                .when(col("days_since_registration").lt(365), "Regular")
                .otherwise("Veteran"))
            .withColumn("email_domain", 
                regexp_extract(col("email"), "@(.+)", 1));
        
        // 3. Product dimension transformations
        logger.info("   Transforming product data...");
        Dataset<Row> productsTransformed = productsDF
            .withColumn("markup_percentage", 
                round((col("retail_price").minus(col("cost_price")))
                    .divide(col("cost_price")).multiply(100), 2))
            .withColumn("price_tier",
                when(col("retail_price").geq(500), "Premium")
                .when(col("retail_price").geq(100), "Standard")
                .otherwise("Budget"));
        
        // 4. Create aggregated tables
        logger.info("   Creating aggregated dimensions...");
        
        // Daily sales summary
        Dataset<Row> dailySales = salesTransformed
            .groupBy("sale_date", "category")
            .agg(
                count("*").alias("transaction_count"),
                sum("final_amount").alias("total_revenue"),
                sum("estimated_profit").alias("total_profit"),
                avg("final_amount").alias("avg_transaction_value"),
                countDistinct("customer_id").alias("unique_customers")
            );
        
        // Customer summary
        Dataset<Row> customerSummary = salesTransformed
            .groupBy("customer_id")
            .agg(
                count("*").alias("total_orders"),
                sum("final_amount").alias("total_spent"),
                sum("estimated_profit").alias("total_profit_generated"),
                avg("final_amount").alias("avg_order_value"),
                max("timestamp").alias("last_order_date"),
                min("timestamp").alias("first_order_date")
            )
            .withColumn("customer_tenure_days",
                datediff(col("last_order_date"), col("first_order_date")));
        
        logger.info("   ✅ Transformed datasets:");
        logger.info("      sales_fact: {} records", salesTransformed.count());
        logger.info("      customer_dim: {} records", customersTransformed.count());
        logger.info("      product_dim: {} records", productsTransformed.count());
        logger.info("      daily_sales_agg: {} records", dailySales.count());
        logger.info("      customer_summary: {} records", customerSummary.count());
        
        return Map.of(
            "sales_fact", salesTransformed,
            "customer_dim", customersTransformed,
            "product_dim", productsTransformed,
            "daily_sales_agg", dailySales,
            "customer_summary", customerSummary
        );
    }
    
    /**
     * Perform data quality validation.
     */
    private static void dataQualityChecks(Map<String, Dataset<Row>> transformed) {
        logger.info("\n🔄 VALIDATE: Performing data quality checks...");
        
        int totalIssues = 0;
        long totalRecords = 0;
        
        for (Map.Entry<String, Dataset<Row>> entry : transformed.entrySet()) {
            String tableName = entry.getKey();
            Dataset<Row> df = entry.getValue();
            
            logger.info("   Checking {}...", tableName);
            
            long tableRecords = df.count();
            totalRecords += tableRecords;
            
            // Null value analysis
            for (String column : df.columns()) {
                long nullCount = df.filter(col(column).isNull()).count();
                if (nullCount > 0) {
                    double nullPercentage = (double) nullCount / tableRecords * 100;
                    if (nullPercentage > 5) {
                        logger.warn("     {}.{}: {:.1f}% nulls", tableName, column, nullPercentage);
                        totalIssues += nullCount;
                    }
                }
            }
            
            // Table-specific business rules
            if (tableName.equals("sales_fact")) {
                long negativeAmounts = df.filter(col("final_amount").lt(0)).count();
                long zeroQuantities = df.filter(col("quantity").leq(0)).count();
                totalIssues += negativeAmounts + zeroQuantities;
                
                if (negativeAmounts > 0) logger.warn("     Negative amounts: {}", negativeAmounts);
                if (zeroQuantities > 0) logger.warn("     Zero quantities: {}", zeroQuantities);
            }
            
            // Duplicate analysis
            long uniqueRecords = df.dropDuplicates().count();
            long duplicateCount = tableRecords - uniqueRecords;
            if (duplicateCount > 0) {
                logger.warn("     Duplicates: {} ({:.1f}%)", 
                    duplicateCount, (double) duplicateCount / tableRecords * 100);
                totalIssues += duplicateCount;
            }
        }
        
        // Calculate overall quality score
        double qualityScore = totalRecords > 0 ? 
            Math.max(0, 100 - ((double) totalIssues / totalRecords * 100)) : 100;
        
        logger.info("   ✅ Data quality checks completed");
        logger.info("      Overall Quality Score: {:.1f}%", qualityScore);
        logger.info("      Total Issues Found: {}", totalIssues);
    }
    
    /**
     * Load transformed data to multiple destinations.
     */
    private static void loadData(Map<String, Dataset<Row>> transformed, String outputPath) {
        logger.info("\n🔄 LOAD: Saving transformed data to {}...", outputPath);
        
        try {
            // 1. Save fact tables (partitioned for performance)
            logger.info("   Saving fact tables...");
            
            Dataset<Row> salesFact = transformed.get("sales_fact");
            salesFact.write()
                .mode(SaveMode.Overwrite)
                .partitionBy("sale_date", "category")
                .parquet(outputPath + "/fact/sales");
            
            logger.info("      ✅ sales_fact: {} records", salesFact.count());
            
            // 2. Save dimension tables
            logger.info("   Saving dimension tables...");
            
            Dataset<Row> customerDim = transformed.get("customer_dim");
            customerDim.write()
                .mode(SaveMode.Overwrite)
                .parquet(outputPath + "/dim/customers");
            
            Dataset<Row> productDim = transformed.get("product_dim");
            productDim.write()
                .mode(SaveMode.Overwrite)
                .parquet(outputPath + "/dim/products");
            
            logger.info("      ✅ customer_dim: {} records", customerDim.count());
            logger.info("      ✅ product_dim: {} records", productDim.count());
            
            // 3. Save aggregated tables
            logger.info("   Saving aggregated tables...");
            
            Dataset<Row> dailySales = transformed.get("daily_sales_agg");
            dailySales.write()
                .mode(SaveMode.Overwrite)
                .parquet(outputPath + "/agg/daily_sales");
            
            Dataset<Row> customerSummary = transformed.get("customer_summary");
            customerSummary.write()
                .mode(SaveMode.Overwrite)
                .parquet(outputPath + "/agg/customer_summary");
            
            logger.info("      ✅ daily_sales_agg: {} records", dailySales.count());
            logger.info("      ✅ customer_summary: {} records", customerSummary.count());
            
            // 4. Save as CSV for external consumption
            logger.info("   Saving CSV exports...");
            
            // Business summary for stakeholders
            Dataset<Row> businessSummary = dailySales.groupBy("category")
                .agg(
                    sum("total_revenue").alias("category_revenue"),
                    sum("transaction_count").alias("category_transactions"),
                    avg("avg_transaction_value").alias("avg_transaction_value")
                );
            
            businessSummary.coalesce(1).write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/export/business_summary");
            
            // Top customers export
            Dataset<Row> topCustomers = customerSummary
                .orderBy(col("total_spent").desc())
                .limit(100);
            topCustomers.coalesce(1).write()
                .mode(SaveMode.Overwrite)
                .option("header", "true")
                .csv(outputPath + "/export/top_customers");
            
            logger.info("   ✅ All data loaded successfully to: {}", outputPath);
            
        } catch (Exception e) {
            logger.error("   ❌ Error loading data: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }
    
    /**
     * Print ETL pipeline summary.
     */
    private static void printPipelineSummary(Map<String, Dataset<Row>> sources, 
                                           Map<String, Dataset<Row>> transformed, 
                                           double processingTime) {
        logger.info("\n" + "=".repeat(70));
        logger.info("📊 ETL PIPELINE EXECUTION SUMMARY");
        logger.info("=".repeat(70));
        
        // Processing metrics
        long totalSourceRecords = sources.values().stream().mapToLong(Dataset::count).sum();
        long totalOutputRecords = transformed.values().stream().mapToLong(Dataset::count).sum();
        
        logger.info("\n⏱️  EXECUTION TIME:");
        logger.info("   Duration: {:.2f} seconds", processingTime);
        
        logger.info("\n📈 PROCESSING METRICS:");
        logger.info("   Source Records: {}", totalSourceRecords);
        logger.info("   Output Records: {}", totalOutputRecords);
        logger.info("   Processing Rate: {:.0f} records/second", totalSourceRecords / processingTime);
        
        logger.info("\n🔄 STAGE BREAKDOWN:");
        logger.info("   Extraction: {} records from {} sources", 
            totalSourceRecords, sources.size());
        logger.info("   Transformation: {} datasets created", transformed.size());
        logger.info("   Loading: {} output datasets", transformed.size());
        
        logger.info("\n" + "=".repeat(70));
    }
    
    /**
     * Main ETL pipeline workflow.
     */
    public static void main(String[] args) {
        // Parse arguments
        Map<String, String> parsedArgs = SparkCommon.parseArgs(args);
        
        if (parsedArgs.containsKey("help")) {
            SparkCommon.printUsage("EtlPipeline");
            return;
        }
        
        int records = Integer.parseInt(parsedArgs.get("records"));
        String outputPath = parsedArgs.get("output-path");
        
        logger.info("🚀 Starting Comprehensive ETL Pipeline");
        logger.info("   Records to process: {}", records);
        logger.info("   Output path: {}", outputPath);
        logger.info("   Master: {}", parsedArgs.get("master"));
        
        // Create Spark session with ETL optimizations
        SparkCommon.SparkConfig config = SparkCommon.createConfigFromArgs(parsedArgs);
        config.setAppName(parsedArgs.get("app-name") + "_ETL_Pipeline");
        
        SparkSession spark = SparkCommon.createSparkSession(config);
        
        // Enable ETL-specific optimizations
        spark.conf().set("spark.sql.adaptive.enabled", "true");
        spark.conf().set("spark.sql.adaptive.coalescePartitions.enabled", "true");
        spark.conf().set("spark.sql.adaptive.skewJoin.enabled", "true");
        spark.conf().set("spark.serializer", "org.apache.spark.serializer.KryoSerializer");
        
        try {
            long startTime = System.currentTimeMillis();
            
            SparkCommon.executeWithErrorHandling(() -> {
                // Execute ETL stages
                logger.info("\n🔄 Executing ETL Pipeline...");
                
                // EXTRACT
                Map<String, Dataset<Row>> sources = extractDataSources(spark, records);
                
                // TRANSFORM
                Map<String, Dataset<Row>> transformed = transformData(sources);
                
                // VALIDATE
                dataQualityChecks(transformed);
                
                // LOAD
                loadData(transformed, outputPath);
                
                long endTime = System.currentTimeMillis();
                double processingTime = (endTime - startTime) / 1000.0;
                
                // Print summary
                printPipelineSummary(sources, transformed, processingTime);
                
            }, "ETL Pipeline");
            
            // Monitor performance
            SparkCommon.monitorJobProgress(spark, "ETL Pipeline");
            
            long endTime = System.currentTimeMillis();
            double processingTime = (endTime - startTime) / 1000.0;
            
            logger.info("\n✅ ETL Pipeline completed successfully!");
            logger.info("   Processed {} source records", records);
            logger.info("   Execution time: {:.2f} seconds", processingTime);
            logger.info("   Results saved to: {}", outputPath);
            
        } finally {
            SparkCommon.cleanupSession(spark);
        }
    }
}
