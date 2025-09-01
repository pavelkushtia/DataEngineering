/**
 * Kafka Consumer Example in C++
 * 
 * This program demonstrates how to consume messages from a Kafka topic using the librdkafka library.
 * It includes error handling, offset management, and performance monitoring.
 * 
 * Usage:
 *     ./consumer [--topic TOPIC] [--group GROUP] [--timeout TIMEOUT]
 * 
 * Example:
 *     ./consumer --topic my-topic --group my-consumer-group --timeout 60
 * 
 * Requirements:
 *     sudo apt-get install librdkafka-dev
 */

#include "kafka_common.h"
#include <librdkafka/rdkafkacpp.h>
#include <iostream>
#include <memory>
#include <atomic>
#include <chrono>

class EnhancedKafkaConsumer {
private:
    std::string topic;
    std::string groupId;
    std::unique_ptr<RdKafka::KafkaConsumer> consumer;
    kafka_common::MessageStats stats;
    std::atomic<bool> running{true};
    
    /**
     * Rebalance callback class
     */
    class RebalanceCallback : public RdKafka::RebalanceCb {
    public:
        void rebalance_cb(RdKafka::KafkaConsumer* consumer,
                         RdKafka::ErrorCode err,
                         std::vector<RdKafka::TopicPartition*>& partitions) override {
            
            if (err == RdKafka::ERR__ASSIGN_PARTITIONS) {
                std::cout << "📋 Partition assignment:" << std::endl;
                for (auto* partition : partitions) {
                    std::cout << "   - " << partition->topic() << "[" << partition->partition() << "]" << std::endl;
                }
                consumer->assign(partitions);
            } else if (err == RdKafka::ERR__REVOKE_PARTITIONS) {
                std::cout << "📋 Partition revocation" << std::endl;
                consumer->unassign();
            } else {
                std::cerr << "❌ Rebalance error: " << RdKafka::err2str(err) << std::endl;
                consumer->unassign();
            }
        }
    };
    
    std::unique_ptr<RebalanceCallback> rebalanceCallback;

public:
    EnhancedKafkaConsumer(const std::string& topicName, const std::string& group) 
        : topic(topicName), groupId(group) {
        kafka_common::utils::setupSignalHandlers(running);
    }
    
    /**
     * Connect to Kafka cluster and subscribe to topic
     */
    bool connect() {
        try {
            auto config = kafka_common::KafkaConfig::getConsumerConfig(groupId);
            
            std::cout << "🔌 Connecting to Kafka brokers: " 
                      << kafka_common::KafkaConfig::getBootstrapServers() << std::endl;
            std::cout << "👥 Consumer group: " << groupId << std::endl;
            
            // Create configuration object
            std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
            
            // Set configuration
            std::string errstr;
            for (const auto& [key, value] : config) {
                if (conf->set(key, value, errstr) != RdKafka::Conf::CONF_OK) {
                    std::cerr << "❌ Failed to set config " << key << ": " << errstr << std::endl;
                    return false;
                }
            }
            
            // Set rebalance callback
            rebalanceCallback = std::make_unique<RebalanceCallback>();
            if (conf->set("rebalance_cb", rebalanceCallback.get(), errstr) != RdKafka::Conf::CONF_OK) {
                std::cerr << "❌ Failed to set rebalance callback: " << errstr << std::endl;
                return false;
            }
            
            // Create consumer
            consumer.reset(RdKafka::KafkaConsumer::create(conf.get(), errstr));
            if (!consumer) {
                std::cerr << "❌ Failed to create consumer: " << errstr << std::endl;
                return false;
            }
            
            // Subscribe to topic
            std::vector<std::string> topics = {topic};
            RdKafka::ErrorCode result = consumer->subscribe(topics);
            if (result != RdKafka::ERR_NO_ERROR) {
                std::cerr << "❌ Failed to subscribe to topic: " << RdKafka::err2str(result) << std::endl;
                return false;
            }
            
            std::cout << "✅ Connected to Kafka and subscribed to topic '" << topic << "'!" << std::endl;
            return true;
            
        } catch (const std::exception& e) {
            std::cerr << "❌ Failed to connect to Kafka: " << e.what() << std::endl;
            return false;
        }
    }
    
    /**
     * Process a received message
     */
    bool processMessage(RdKafka::Message* message) {
        try {
            // Extract message details
            std::string topic = message->topic_name();
            int32_t partition = message->partition();
            int64_t offset = message->offset();
            std::string key = message->key() ? *message->key() : "";
            std::string value(static_cast<char*>(message->payload()), message->len());
            int64_t timestamp = message->timestamp().timestamp;
            
            stats.recordReceived();
            
            // Print message details
            std::cout << "📨 Received message:" << std::endl;
            std::cout << "   🔑 Key: " << key << std::endl;
            std::cout << "   📋 Topic: " << topic << "[" << partition << "] @ offset " << offset << std::endl;
            std::cout << "   ⏰ Timestamp: " << timestamp << std::endl;
            
            // Parse JSON message (basic parsing)
            std::string messageId = kafka_common::MessageUtils::extractJsonField(value, "id");
            std::string messageType = kafka_common::MessageUtils::extractJsonField(value, "type");
            
            std::cout << "   📦 Message ID: " << (messageId.empty() ? "N/A" : messageId) << std::endl;
            std::cout << "   📊 Message Type: " << (messageType.empty() ? "N/A" : messageType) << std::endl;
            
            // Process specific message types
            processMessageByType(value, messageType);
            
            return true;
            
        } catch (const std::exception& e) {
            std::cerr << "❌ Error processing message: " << e.what() << std::endl;
            stats.recordError();
            return false;
        }
    }
    
    /**
     * Process message based on its type
     */
    void processMessageByType(const std::string& jsonMessage, const std::string& messageType) {
        if (messageType == "producer_demo") {
            // Extract data fields (simple approach for demo)
            size_t dataPos = jsonMessage.find("\"data\":");
            if (dataPos != std::string::npos) {
                size_t dataStart = jsonMessage.find("{", dataPos);
                size_t dataEnd = jsonMessage.find("}", dataStart);
                if (dataStart != std::string::npos && dataEnd != std::string::npos) {
                    std::string dataSection = jsonMessage.substr(dataStart, dataEnd - dataStart + 1);
                    
                    std::string userId = kafka_common::MessageUtils::extractJsonField(dataSection, "user_id");
                    std::string action = kafka_common::MessageUtils::extractJsonField(dataSection, "action");
                    std::string productId = kafka_common::MessageUtils::extractJsonField(dataSection, "product_id");
                    std::string value = kafka_common::MessageUtils::extractJsonField(dataSection, "value");
                    
                    std::cout << "   👤 User: " << userId << std::endl;
                    std::cout << "   🎯 Action: " << action << std::endl;
                    std::cout << "   📦 Product: " << productId << std::endl;
                    std::cout << "   💰 Value: " << value << std::endl;
                }
            }
            
        } else if (messageType == "order") {
            size_t dataPos = jsonMessage.find("\"data\":");
            if (dataPos != std::string::npos) {
                size_t dataStart = jsonMessage.find("{", dataPos);
                size_t dataEnd = jsonMessage.find("}", dataStart);
                if (dataStart != std::string::npos && dataEnd != std::string::npos) {
                    std::string dataSection = jsonMessage.substr(dataStart, dataEnd - dataStart + 1);
                    
                    std::string orderId = kafka_common::MessageUtils::extractJsonField(dataSection, "order_id");
                    std::string total = kafka_common::MessageUtils::extractJsonField(dataSection, "total_amount");
                    std::cout << "   🛒 Order ID: " << orderId << std::endl;
                    std::cout << "   💵 Total: $" << total << std::endl;
                }
            }
            
        } else if (messageType == "user_event") {
            size_t dataPos = jsonMessage.find("\"data\":");
            if (dataPos != std::string::npos) {
                size_t dataStart = jsonMessage.find("{", dataPos);
                size_t dataEnd = jsonMessage.find("}", dataStart);
                if (dataStart != std::string::npos && dataEnd != std::string::npos) {
                    std::string dataSection = jsonMessage.substr(dataStart, dataEnd - dataStart + 1);
                    
                    std::string eventName = kafka_common::MessageUtils::extractJsonField(dataSection, "event_name");
                    std::string sessionId = kafka_common::MessageUtils::extractJsonField(dataSection, "session_id");
                    std::cout << "   📊 Event: " << eventName << std::endl;
                    std::cout << "   🔗 Session: " << sessionId << std::endl;
                }
            }
        }
        
        std::cout << std::endl; // Empty line for readability
    }
    
    /**
     * Consume messages from the Kafka topic
     */
    void consumeMessages(int timeoutSeconds) {
        std::cout << "🚀 Starting to consume from topic '" << topic << "'" << std::endl;
        if (timeoutSeconds > 0) {
            std::cout << "⏰ Timeout: " << timeoutSeconds << " seconds" << std::endl;
        } else {
            std::cout << "⏰ Timeout: infinite (Ctrl+C to stop)" << std::endl;
        }
        std::cout << std::string(50, '=') << std::endl;
        
        auto startTime = std::chrono::steady_clock::now();
        auto lastStatsTime = startTime;
        
        try {
            while (running.load()) {
                // Check timeout
                if (timeoutSeconds > 0) {
                    auto now = std::chrono::steady_clock::now();
                    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - startTime).count();
                    if (elapsed >= timeoutSeconds) {
                        std::cout << "⏰ Timeout reached (" << timeoutSeconds << "s)" << std::endl;
                        break;
                    }
                }
                
                // Poll for messages
                std::unique_ptr<RdKafka::Message> message(consumer->consume(1000)); // 1 second timeout
                
                if (message) {
                    switch (message->err()) {
                        case RdKafka::ERR_NO_ERROR:
                            processMessage(message.get());
                            break;
                            
                        case RdKafka::ERR__TIMED_OUT:
                            // Timeout is expected, continue polling
                            break;
                            
                        case RdKafka::ERR__PARTITION_EOF:
                            std::cout << "📝 Reached end of partition " << message->partition() << std::endl;
                            break;
                            
                        default:
                            std::cerr << "❌ Consumer error: " << message->errstr() << std::endl;
                            stats.recordError();
                            break;
                    }
                }
                
                // Print stats every 10 seconds
                auto currentTime = std::chrono::steady_clock::now();
                auto timeSinceLastStats = std::chrono::duration_cast<std::chrono::seconds>(currentTime - lastStatsTime).count();
                if (timeSinceLastStats >= 10) {
                    stats.printStats();
                    lastStatsTime = currentTime;
                }
            }
            
        } catch (const std::exception& e) {
            std::cerr << "❌ Error during consumption: " << e.what() << std::endl;
            stats.recordError();
        }
        
        std::cout << "✅ Finished consuming messages!" << std::endl;
        stats.printStats();
    }
    
    /**
     * Close the consumer connection
     */
    void close() {
        if (consumer) {
            std::cout << "🔌 Closing consumer connection..." << std::endl;
            consumer->close();
            consumer.reset();
            std::cout << "✅ Consumer closed successfully" << std::endl;
        }
    }
};

int main(int argc, char* argv[]) {
    kafka_common::Args args(argc, argv);
    
    // Check for help flag
    if (args.hasFlag("--help")) {
        args.printUsage("consumer");
        return 0;
    }
    
    // Parse arguments
    std::string topic = args.get("--topic", kafka_common::KafkaConfig::getDefaultTopic());
    std::string group = args.get("--group", "building-blocks-consumer-group");
    int timeout = args.getInt("--timeout", -1);
    
    kafka_common::utils::printHeader("🎯 Kafka Consumer Example");
    kafka_common::utils::printConfig(topic, -1, -1, group);
    if (timeout > 0) {
        std::cout << "⏰ Timeout: " << timeout << "s" << std::endl;
    } else {
        std::cout << "⏰ Timeout: infinite" << std::endl;
    }
    std::cout << std::string(50, '=') << std::endl;
    
    EnhancedKafkaConsumer consumer(topic, group);
    
    try {
        // Connect to Kafka
        if (!consumer.connect()) {
            return 1;
        }
        
        // Consume messages
        consumer.consumeMessages(timeout);
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Unexpected error: " << e.what() << std::endl;
        return 1;
    }
    
    consumer.close();
    return 0;
}
