/**
 * Kafka Producer Example in C++
 * 
 * This program demonstrates how to produce messages to a Kafka topic using the librdkafka library.
 * It includes error handling, delivery confirmation, and performance monitoring.
 * 
 * Usage:
 *     ./producer [--topic TOPIC] [--count COUNT] [--rate RATE]
 * 
 * Example:
 *     ./producer --topic my-topic --count 1000 --rate 10
 * 
 * Requirements:
 *     sudo apt-get install librdkafka-dev
 */

#include "kafka_common.h"
#include <librdkafka/rdkafkacpp.h>
#include <iostream>
#include <memory>
#include <atomic>

class EnhancedKafkaProducer {
private:
    std::string topic;
    std::unique_ptr<RdKafka::Producer> producer;
    std::unique_ptr<RdKafka::Topic> kafkaTopic;
    kafka_common::MessageStats stats;
    std::atomic<bool> running{true};
    
    /**
     * Delivery report callback class
     */
    class DeliveryReportCallback : public RdKafka::DeliveryReportCb {
    private:
        kafka_common::MessageStats& stats;
        
    public:
        DeliveryReportCallback(kafka_common::MessageStats& s) : stats(s) {}
        
        void dr_cb(RdKafka::Message& message) override {
            if (message.err() == RdKafka::ERR_NO_ERROR) {
                stats.recordSent();
                std::cout << "✅ Message sent to " << message.topic_name()
                          << "[" << message.partition() << "] at offset " << message.offset() << std::endl;
            } else {
                stats.recordError();
                std::cout << "❌ Message delivery failed: " << message.errstr() << std::endl;
            }
        }
    };
    
    std::unique_ptr<DeliveryReportCallback> deliveryCallback;

public:
    EnhancedKafkaProducer(const std::string& topicName) : topic(topicName) {
        kafka_common::utils::setupSignalHandlers(running);
    }
    
    /**
     * Connect to Kafka cluster
     */
    bool connect() {
        try {
            auto config = kafka_common::KafkaConfig::getProducerConfig();
            
            std::cout << "🔌 Connecting to Kafka brokers: " 
                      << kafka_common::KafkaConfig::getBootstrapServers() << std::endl;
            
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
            
            // Set delivery report callback
            deliveryCallback = std::make_unique<DeliveryReportCallback>(stats);
            if (conf->set("dr_cb", deliveryCallback.get(), errstr) != RdKafka::Conf::CONF_OK) {
                std::cerr << "❌ Failed to set delivery callback: " << errstr << std::endl;
                return false;
            }
            
            // Create producer
            producer.reset(RdKafka::Producer::create(conf.get(), errstr));
            if (!producer) {
                std::cerr << "❌ Failed to create producer: " << errstr << std::endl;
                return false;
            }
            
            // Create topic object
            std::unique_ptr<RdKafka::Conf> topicConf(RdKafka::Conf::create(RdKafka::Conf::CONF_TOPIC));
            kafkaTopic.reset(RdKafka::Topic::create(producer.get(), topic, topicConf.get(), errstr));
            if (!kafkaTopic) {
                std::cerr << "❌ Failed to create topic: " << errstr << std::endl;
                return false;
            }
            
            std::cout << "✅ Connected to Kafka successfully!" << std::endl;
            return true;
            
        } catch (const std::exception& e) {
            std::cerr << "❌ Failed to connect to Kafka: " << e.what() << std::endl;
            return false;
        }
    }
    
    /**
     * Send a message to the Kafka topic
     */
    bool sendMessage(const std::string& key, const std::string& message) {
        try {
            RdKafka::ErrorCode result = producer->produce(
                kafkaTopic.get(),
                RdKafka::Topic::PARTITION_UA,  // Automatic partition assignment
                RdKafka::Producer::RK_MSG_COPY,
                const_cast<char*>(message.c_str()),
                message.size(),
                &key,
                nullptr  // message headers
            );
            
            if (result != RdKafka::ERR_NO_ERROR) {
                std::cerr << "❌ Error sending message: " << RdKafka::err2str(result) << std::endl;
                stats.recordError();
                return false;
            }
            
            // Poll for delivery reports
            producer->poll(0);
            
            return true;
            
        } catch (const std::exception& e) {
            std::cerr << "❌ Error sending message: " << e.what() << std::endl;
            stats.recordError();
            return false;
        }
    }
    
    /**
     * Produce a specified number of messages
     */
    void produceMessages(int count, double rate) {
        std::cout << "🚀 Starting to produce " << count << " messages to topic '" << topic << "'" << std::endl;
        if (rate > 0) {
            std::cout << "📊 Rate limit: " << rate << " messages/second" << std::endl;
        } else {
            std::cout << "📊 Rate limit: unlimited" << std::endl;
        }
        
        int sleepTimeMs = rate > 0 ? static_cast<int>(1000.0 / rate) : 0;
        
        for (int i = 0; i < count && running.load(); i++) {
            // Create sample message
            std::string messageData = kafka_common::MessageUtils::createSampleMessage(i, "producer_demo");
            std::string messageKey = kafka_common::MessageUtils::generateMessageKey(i);
            
            // Send message
            bool success = sendMessage(messageKey, messageData);
            
            if (success) {
                std::cout << "📤 Sent message " << (i + 1) << "/" << count << ": " << messageKey << std::endl;
            }
            
            // Rate limiting
            if (sleepTimeMs > 0) {
                kafka_common::utils::sleepMs(sleepTimeMs);
            }
            
            // Print stats every 100 messages
            if ((i + 1) % 100 == 0) {
                stats.printStats();
            }
        }
        
        // Wait for delivery reports and flush
        std::cout << "🔄 Flushing remaining messages..." << std::endl;
        if (producer) {
            producer->flush(30000);  // 30 second timeout
        }
        
        std::cout << "✅ Finished producing messages!" << std::endl;
        stats.printStats();
    }
    
    /**
     * Close the producer connection
     */
    void close() {
        if (producer) {
            std::cout << "🔌 Closing producer connection..." << std::endl;
            producer.reset();
            std::cout << "✅ Producer closed successfully" << std::endl;
        }
    }
};

int main(int argc, char* argv[]) {
    kafka_common::Args args(argc, argv);
    
    // Check for help flag
    if (args.hasFlag("--help")) {
        args.printUsage("producer");
        return 0;
    }
    
    // Parse arguments
    std::string topic = args.get("--topic", kafka_common::KafkaConfig::getDefaultTopic());
    int count = args.getInt("--count", 10);
    double rate = args.getDouble("--rate", 1.0);
    
    kafka_common::utils::printHeader("🎯 Kafka Producer Example");
    kafka_common::utils::printConfig(topic, count, rate);
    
    EnhancedKafkaProducer producer(topic);
    
    try {
        // Connect to Kafka
        if (!producer.connect()) {
            return 1;
        }
        
        // Produce messages
        producer.produceMessages(count, rate);
        
    } catch (const std::exception& e) {
        std::cerr << "❌ Unexpected error: " << e.what() << std::endl;
        return 1;
    }
    
    producer.close();
    return 0;
}
