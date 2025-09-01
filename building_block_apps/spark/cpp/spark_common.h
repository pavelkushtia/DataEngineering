#ifndef SPARK_COMMON_H
#define SPARK_COMMON_H

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <chrono>
#include <random>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <cstdlib>
#include <algorithm>

/**
 * Common utilities and configuration for Spark building block applications in C++.
 * 
 * This header provides:
 * - Configuration management for Spark applications
 * - Command line argument parsing
 * - Sample data generation utilities
 * - Performance monitoring helpers
 * - Error handling patterns
 * - Utility functions for common operations
 * 
 * Note: C++ Spark examples use system calls to spark-submit for execution,
 * as there is no direct C++ API for Apache Spark. These examples demonstrate
 * how to integrate C++ applications with Spark workflows.
 */

namespace SparkCommon {

/**
 * Configuration structure for Spark applications.
 */
struct SparkConfig {
    std::string appName;
    std::string master;
    std::string executorMemory;
    std::string executorCores;
    std::string driverMemory;
    std::string kafkaServers;
    std::string checkpointDir;
    std::string warehouseDir;
    
    // Constructor with defaults
    SparkConfig() : 
        appName("SparkCppBuildingBlock"),
        master("spark://192.168.1.184:7077"),
        executorMemory("2g"),
        executorCores("2"),
        driverMemory("1g"),
        kafkaServers("192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092"),
        checkpointDir("/tmp/spark-checkpoints"),
        warehouseDir("/home/spark/spark/warehouse") {}
};

/**
 * Command line arguments structure.
 */
struct CommandLineArgs {
    std::string master;
    std::string appName;
    std::string executorMemory;
    std::string executorCores;
    int records;
    std::string outputPath;
    std::string kafkaTopic;
    int duration;
    bool verbose;
    bool help;
    
    // Constructor with defaults
    CommandLineArgs() :
        master("spark://192.168.1.184:7077"),
        appName("SparkCppBuildingBlock"),
        executorMemory("2g"),
        executorCores("2"),
        records(10000),
        outputPath("/tmp/spark-output"),
        kafkaTopic("spark-demo"),
        duration(60),
        verbose(false),
        help(false) {}
};

/**
 * Sample data record structure.
 */
struct SampleRecord {
    std::string userId;
    std::string productId;
    std::string category;
    std::string action;
    std::string timestamp;
    double price;
    int quantity;
    std::string sessionId;
    bool isPremium;
    std::string region;
    
    // Convert to CSV string
    std::string toCSV() const;
    
    // Convert to JSON string
    std::string toJSON() const;
};

/**
 * Performance metrics structure.
 */
struct PerformanceMetrics {
    std::chrono::high_resolution_clock::time_point startTime;
    std::chrono::high_resolution_clock::time_point endTime;
    long recordsProcessed;
    std::string operationName;
    
    PerformanceMetrics(const std::string& name) : 
        operationName(name),
        recordsProcessed(0) {
        startTime = std::chrono::high_resolution_clock::now();
    }
    
    void finish(long records = 0) {
        endTime = std::chrono::high_resolution_clock::now();
        recordsProcessed = records;
    }
    
    double getDurationSeconds() const {
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
        return duration.count() / 1000.0;
    }
    
    double getRecordsPerSecond() const {
        double duration = getDurationSeconds();
        return duration > 0 ? recordsProcessed / duration : 0;
    }
};

// Function declarations

/**
 * Parse command line arguments.
 * 
 * @param argc Argument count
 * @param argv Argument values
 * @return Parsed command line arguments
 */
CommandLineArgs parseCommandLineArgs(int argc, char* argv[]);

/**
 * Print usage information.
 * 
 * @param programName Name of the program
 */
void printUsage(const std::string& programName);

/**
 * Create SparkConfig from command line arguments.
 * 
 * @param args Parsed command line arguments
 * @return SparkConfig object
 */
SparkConfig createSparkConfig(const CommandLineArgs& args);

/**
 * Generate sample e-commerce data.
 * 
 * @param numRecords Number of records to generate
 * @return Vector of sample records
 */
std::vector<SampleRecord> generateSampleData(int numRecords);

/**
 * Save sample data to CSV file.
 * 
 * @param data Vector of sample records
 * @param filename Output filename
 */
void saveSampleDataToCSV(const std::vector<SampleRecord>& data, const std::string& filename);

/**
 * Save sample data to JSON file.
 * 
 * @param data Vector of sample records
 * @param filename Output filename
 */
void saveSampleDataToJSON(const std::vector<SampleRecord>& data, const std::string& filename);

/**
 * Execute Spark job using spark-submit.
 * 
 * @param config Spark configuration
 * @param pythonScript Path to Python script
 * @param args Additional arguments for the script
 * @return Exit code from spark-submit
 */
int executeSparkJob(const SparkConfig& config, const std::string& pythonScript, 
                   const std::vector<std::string>& args = {});

/**
 * Monitor job progress and print metrics.
 * 
 * @param metrics Performance metrics object
 */
void printPerformanceMetrics(const PerformanceMetrics& metrics);

/**
 * Create directory if it doesn't exist.
 * 
 * @param path Directory path
 * @return True if directory exists or was created successfully
 */
bool createDirectory(const std::string& path);

/**
 * Get current timestamp as string.
 * 
 * @param format Format string (default: "%Y-%m-%d %H:%M:%S")
 * @return Formatted timestamp string
 */
std::string getCurrentTimestamp(const std::string& format = "%Y-%m-%d %H:%M:%S");

/**
 * Execute system command and capture output.
 * 
 * @param command Command to execute
 * @param output Reference to store command output
 * @return Exit code from command
 */
int executeCommand(const std::string& command, std::string& output);

/**
 * Check if Spark cluster is accessible.
 * 
 * @param master Spark master URL
 * @return True if cluster is accessible
 */
bool checkSparkCluster(const std::string& master);

/**
 * Print data quality summary.
 * 
 * @param data Vector of sample records
 */
void printDataQualitySummary(const std::vector<SampleRecord>& data);

/**
 * Generate basic statistics for numeric data.
 * 
 * @param values Vector of numeric values
 * @return Map containing statistics (mean, min, max, stddev, etc.)
 */
std::map<std::string, double> calculateStatistics(const std::vector<double>& values);

/**
 * Log message with timestamp.
 * 
 * @param level Log level (INFO, WARN, ERROR)
 * @param message Log message
 */
void log(const std::string& level, const std::string& message);

/**
 * Helper macros for logging.
 */
#define LOG_INFO(msg) SparkCommon::log("INFO", msg)
#define LOG_WARN(msg) SparkCommon::log("WARN", msg)
#define LOG_ERROR(msg) SparkCommon::log("ERROR", msg)

/**
 * Exception class for Spark-related errors.
 */
class SparkException : public std::runtime_error {
public:
    explicit SparkException(const std::string& message) : std::runtime_error(message) {}
};

/**
 * RAII helper for performance measurement.
 */
class PerformanceTimer {
private:
    PerformanceMetrics& metrics;
    
public:
    explicit PerformanceTimer(PerformanceMetrics& m) : metrics(m) {}
    
    ~PerformanceTimer() {
        metrics.finish();
        printPerformanceMetrics(metrics);
    }
};

} // namespace SparkCommon

#endif // SPARK_COMMON_H
