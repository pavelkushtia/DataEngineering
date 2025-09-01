#include "kafka_common.h"
#include <thread>
#include <csignal>
#include <cmath>
#include <regex>

namespace kafka_common {

// Global atomic for signal handling
static std::atomic<bool>* global_running = nullptr;

// Signal handler function
void signalHandler(int signal) {
    std::cout << "\n🛑 Received signal " << signal << ", shutting down gracefully..." << std::endl;
    if (global_running) {
        global_running->store(false);
    }
}

// KafkaConfig implementation
std::map<std::string, std::string> KafkaConfig::getCommonConfig() {
    return {
        {"bootstrap.servers", "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092"},
        {"security.protocol", "PLAINTEXT"},
        {"acks", "all"},
        {"retries", "3"},
        {"retry.backoff.ms", "100"},
        {"request.timeout.ms", "30000"},
        {"delivery.timeout.ms", "120000"}
    };
}

std::map<std::string, std::string> KafkaConfig::getProducerConfig() {
    auto config = getCommonConfig();
    
    // Producer specific settings
    config["enable.idempotence"] = "true";
    config["max.in.flight.requests.per.connection"] = "5";
    config["compression.type"] = "snappy";
    config["batch.size"] = "16384";
    config["linger.ms"] = "10";
    config["buffer.memory"] = "33554432";
    
    return config;
}

std::map<std::string, std::string> KafkaConfig::getConsumerConfig(const std::string& groupId) {
    auto config = getCommonConfig();
    
    // Consumer specific settings
    config["group.id"] = groupId;
    config["auto.offset.reset"] = "earliest";
    config["enable.auto.commit"] = "true";
    config["auto.commit.interval.ms"] = "1000";
    config["session.timeout.ms"] = "30000";
    config["heartbeat.interval.ms"] = "3000";
    config["max.poll.records"] = "500";
    config["max.poll.interval.ms"] = "300000";
    
    return config;
}

std::string KafkaConfig::getDefaultTopic() {
    return "building-blocks-demo";
}

std::string KafkaConfig::getBootstrapServers() {
    return "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092";
}

// MessageUtils implementation
std::string MessageUtils::createSampleMessage(int messageId, const std::string& messageType) {
    long long timestamp = getCurrentTimestamp();
    
    std::ostringstream json;
    json << "{"
         << "\"id\":" << messageId << ","
         << "\"type\":\"" << messageType << "\","
         << "\"timestamp\":" << timestamp << ","
         << "\"data\":{"
         << "\"user_id\":\"user_" << (messageId % 1000) << "\","
         << "\"action\":\"" << (messageId % 2 == 0 ? "view_product" : "add_to_cart") << "\","
         << "\"product_id\":\"product_" << (messageId % 100) << "\","
         << "\"session_id\":\"session_" << (messageId / 10) << "\","
         << "\"value\":" << std::fixed << std::setprecision(2) << (std::fmod(messageId * 1.23, 1000))
         << "},"
         << "\"metadata\":{"
         << "\"source\":\"cpp_producer\","
         << "\"version\":\"1.0\","
         << "\"environment\":\"development\""
         << "}"
         << "}";
    
    return json.str();
}

std::string MessageUtils::extractJsonField(const std::string& json, const std::string& fieldName) {
    try {
        // Simple string-based JSON parsing (not robust, but sufficient for examples)
        std::string pattern = "\"" + fieldName + "\"";
        size_t pos = json.find(pattern);
        if (pos == std::string::npos) {
            return "";
        }
        
        // Find the colon
        pos = json.find(":", pos);
        if (pos == std::string::npos) {
            return "";
        }
        
        // Skip whitespace and optional quote
        pos++;
        while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\t')) {
            pos++;
        }
        
        bool hasQuotes = (pos < json.length() && json[pos] == '"');
        if (hasQuotes) {
            pos++;
        }
        
        // Find the end
        size_t end = pos;
        if (hasQuotes) {
            end = json.find('"', pos);
        } else {
            while (end < json.length() && json[end] != ',' && json[end] != '}' && json[end] != ' ') {
                end++;
            }
        }
        
        if (end == std::string::npos) {
            end = json.length();
        }
        
        return json.substr(pos, end - pos);
        
    } catch (const std::exception& e) {
        return "";
    }
}

long long MessageUtils::getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
}

std::string MessageUtils::generateMessageKey(int messageId) {
    return "key_" + std::to_string(messageId);
}

// MessageStats implementation
MessageStats::MessageStats() : startTime(std::chrono::steady_clock::now()) {}

void MessageStats::recordSent() {
    sentCount.fetch_add(1);
}

void MessageStats::recordReceived() {
    receivedCount.fetch_add(1);
}

void MessageStats::recordError() {
    errorCount.fetch_add(1);
}

void MessageStats::printStats() const {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - startTime).count();
    
    double sendRate = elapsed > 0 ? static_cast<double>(sentCount.load()) / elapsed : 0.0;
    double receiveRate = elapsed > 0 ? static_cast<double>(receivedCount.load()) / elapsed : 0.0;
    
    std::cout << "📊 Stats: Sent=" << sentCount.load()
              << ", Received=" << receivedCount.load()
              << ", Errors=" << errorCount.load()
              << ", Elapsed=" << elapsed << "s"
              << ", Send Rate=" << std::fixed << std::setprecision(2) << sendRate << "/s"
              << ", Receive Rate=" << std::fixed << std::setprecision(2) << receiveRate << "/s"
              << std::endl;
}

// Args implementation
Args::Args(int argc, char* argv[]) {
    for (int i = 1; i < argc - 1; i += 2) {
        if (argv[i][0] == '-' && argv[i][1] == '-') {
            argMap[argv[i]] = argv[i + 1];
        }
    }
    
    // Handle flags without values
    if (argc > 1 && argv[argc - 1][0] == '-' && argv[argc - 1][1] == '-') {
        argMap[argv[argc - 1]] = "true";
    }
}

std::string Args::get(const std::string& flag, const std::string& defaultValue) const {
    auto it = argMap.find(flag);
    return (it != argMap.end()) ? it->second : defaultValue;
}

int Args::getInt(const std::string& flag, int defaultValue) const {
    std::string value = get(flag, std::to_string(defaultValue));
    try {
        return std::stoi(value);
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Invalid integer value for " << flag << ": " << value 
                  << ", using default: " << defaultValue << std::endl;
        return defaultValue;
    }
}

double Args::getDouble(const std::string& flag, double defaultValue) const {
    std::string value = get(flag, std::to_string(defaultValue));
    try {
        return std::stod(value);
    } catch (const std::exception& e) {
        std::cerr << "⚠️  Invalid double value for " << flag << ": " << value 
                  << ", using default: " << defaultValue << std::endl;
        return defaultValue;
    }
}

bool Args::hasFlag(const std::string& flag) const {
    return argMap.find(flag) != argMap.end();
}

void Args::printUsage(const std::string& programName) const {
    std::cout << "Usage: " << programName << " [options]" << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  --topic TOPIC        Kafka topic (default: " << KafkaConfig::getDefaultTopic() << ")" << std::endl;
    std::cout << "  --count COUNT        Number of messages (default: 10)" << std::endl;
    std::cout << "  --rate RATE          Messages per second (default: 1.0)" << std::endl;
    std::cout << "  --group GROUP        Consumer group ID (default: building-blocks-consumer-group)" << std::endl;
    std::cout << "  --timeout TIMEOUT    Timeout in seconds (default: infinite)" << std::endl;
    std::cout << "  --help               Show this help message" << std::endl;
}

// Utils implementation
namespace utils {

void sleepMs(int milliseconds) {
    std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

void setupSignalHandlers(std::atomic<bool>& running) {
    global_running = &running;
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);
}

void printHeader(const std::string& title) {
    std::cout << title << std::endl;
    std::cout << std::string(50, '=') << std::endl;
}

void printConfig(const std::string& topic, int count, double rate, const std::string& group) {
    std::cout << "📌 Topic: " << topic << std::endl;
    if (count >= 0) {
        std::cout << "📊 Message count: " << count << std::endl;
    }
    if (rate >= 0) {
        std::cout << "⚡ Rate: " << rate << " messages/second" << std::endl;
    }
    if (!group.empty()) {
        std::cout << "👥 Group: " << group << std::endl;
    }
    std::cout << std::string(50, '=') << std::endl;
}

} // namespace utils

} // namespace kafka_common
