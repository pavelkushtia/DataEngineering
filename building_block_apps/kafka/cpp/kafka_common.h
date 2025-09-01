#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <chrono>
#include <atomic>
#include <iostream>
#include <sstream>
#include <iomanip>

/**
 * Common utilities for Kafka C++ examples.
 * 
 * This header provides shared configuration and utilities for Kafka producers and consumers
 * using the librdkafka library.
 */

namespace kafka_common {

/**
 * Kafka configuration helper class
 */
class KafkaConfig {
public:
    /**
     * Get common Kafka configuration
     */
    static std::map<std::string, std::string> getCommonConfig();
    
    /**
     * Get producer-specific configuration
     */
    static std::map<std::string, std::string> getProducerConfig();
    
    /**
     * Get consumer-specific configuration
     */
    static std::map<std::string, std::string> getConsumerConfig(const std::string& groupId);
    
    /**
     * Get default topic name
     */
    static std::string getDefaultTopic();
    
    /**
     * Get bootstrap servers
     */
    static std::string getBootstrapServers();
};

/**
 * Message utilities
 */
class MessageUtils {
public:
    /**
     * Create a sample JSON message for testing
     */
    static std::string createSampleMessage(int messageId, const std::string& messageType);
    
    /**
     * Parse a simple JSON field value (basic regex-free parsing)
     */
    static std::string extractJsonField(const std::string& json, const std::string& fieldName);
    
    /**
     * Get current timestamp in milliseconds
     */
    static long long getCurrentTimestamp();
    
    /**
     * Generate a message key
     */
    static std::string generateMessageKey(int messageId);
};

/**
 * Statistics tracker for messages
 */
class MessageStats {
private:
    std::atomic<int> sentCount{0};
    std::atomic<int> receivedCount{0};
    std::atomic<int> errorCount{0};
    std::chrono::steady_clock::time_point startTime;

public:
    MessageStats();
    
    void recordSent();
    void recordReceived();
    void recordError();
    
    void printStats() const;
    
    int getSentCount() const { return sentCount.load(); }
    int getReceivedCount() const { return receivedCount.load(); }
    int getErrorCount() const { return errorCount.load(); }
};

/**
 * Command line argument parser
 */
class Args {
private:
    std::map<std::string, std::string> argMap;
    
public:
    Args(int argc, char* argv[]);
    
    std::string get(const std::string& flag, const std::string& defaultValue) const;
    int getInt(const std::string& flag, int defaultValue) const;
    double getDouble(const std::string& flag, double defaultValue) const;
    bool hasFlag(const std::string& flag) const;
    
    void printUsage(const std::string& programName) const;
};

/**
 * Utility functions
 */
namespace utils {
    /**
     * Sleep for specified milliseconds
     */
    void sleepMs(int milliseconds);
    
    /**
     * Setup signal handlers for graceful shutdown
     */
    void setupSignalHandlers(std::atomic<bool>& running);
    
    /**
     * Print a formatted header
     */
    void printHeader(const std::string& title);
    
    /**
     * Print program configuration
     */
    void printConfig(const std::string& topic, int count = -1, double rate = -1, 
                    const std::string& group = "");
}

} // namespace kafka_common
