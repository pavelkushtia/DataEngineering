#include "spark_common.h"
#include <cstring>
#include <sys/stat.h>
#include <unistd.h>
#include <cmath>

namespace SparkCommon {

std::string SampleRecord::toCSV() const {
    std::ostringstream oss;
    oss << userId << ","
        << productId << ","
        << category << ","
        << action << ","
        << timestamp << ","
        << std::fixed << std::setprecision(2) << price << ","
        << quantity << ","
        << sessionId << ","
        << (isPremium ? "true" : "false") << ","
        << region;
    return oss.str();
}

std::string SampleRecord::toJSON() const {
    std::ostringstream oss;
    oss << "{"
        << "\"user_id\":\"" << userId << "\","
        << "\"product_id\":\"" << productId << "\","
        << "\"category\":\"" << category << "\","
        << "\"action\":\"" << action << "\","
        << "\"timestamp\":\"" << timestamp << "\","
        << "\"price\":" << std::fixed << std::setprecision(2) << price << ","
        << "\"quantity\":" << quantity << ","
        << "\"session_id\":\"" << sessionId << "\","
        << "\"is_premium\":" << (isPremium ? "true" : "false") << ","
        << "\"region\":\"" << region << "\""
        << "}";
    return oss.str();
}

CommandLineArgs parseCommandLineArgs(int argc, char* argv[]) {
    CommandLineArgs args;
    
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "--help" || arg == "-h") {
            args.help = true;
        } else if (arg == "--verbose" || arg == "-v") {
            args.verbose = true;
        } else if (arg == "--master" && i + 1 < argc) {
            args.master = argv[++i];
        } else if (arg == "--app-name" && i + 1 < argc) {
            args.appName = argv[++i];
        } else if (arg == "--executor-memory" && i + 1 < argc) {
            args.executorMemory = argv[++i];
        } else if (arg == "--executor-cores" && i + 1 < argc) {
            args.executorCores = argv[++i];
        } else if (arg == "--records" && i + 1 < argc) {
            args.records = std::stoi(argv[++i]);
        } else if (arg == "--output-path" && i + 1 < argc) {
            args.outputPath = argv[++i];
        } else if (arg == "--kafka-topic" && i + 1 < argc) {
            args.kafkaTopic = argv[++i];
        } else if (arg == "--duration" && i + 1 < argc) {
            args.duration = std::stoi(argv[++i]);
        }
    }
    
    return args;
}

void printUsage(const std::string& programName) {
    std::cout << "Usage: " << programName << " [OPTIONS]\n";
    std::cout << "Options:\n";
    std::cout << "  --master URL              Spark master URL (default: spark://192.168.1.184:7077)\n";
    std::cout << "  --app-name NAME           Spark application name (default: SparkCppBuildingBlock)\n";
    std::cout << "  --executor-memory SIZE    Executor memory (default: 2g)\n";
    std::cout << "  --executor-cores NUM      Executor cores (default: 2)\n";
    std::cout << "  --records NUM             Number of records to process (default: 10000)\n";
    std::cout << "  --output-path PATH        Output path for results (default: /tmp/spark-output)\n";
    std::cout << "  --kafka-topic TOPIC       Kafka topic for streaming (default: spark-demo)\n";
    std::cout << "  --duration SECONDS        Duration for streaming jobs (default: 60)\n";
    std::cout << "  --verbose, -v             Enable verbose logging\n";
    std::cout << "  --help, -h                Show this help message\n";
}

SparkConfig createSparkConfig(const CommandLineArgs& args) {
    SparkConfig config;
    config.appName = args.appName;
    config.master = args.master;
    config.executorMemory = args.executorMemory;
    config.executorCores = args.executorCores;
    return config;
}

std::vector<SampleRecord> generateSampleData(int numRecords) {
    LOG_INFO("🔄 Generating " + std::to_string(numRecords) + " sample records...");
    
    std::vector<SampleRecord> data;
    data.reserve(numRecords);
    
    std::vector<std::string> categories = {"electronics", "clothing", "books", "home", "sports"};
    std::vector<std::string> actions = {"view", "add_to_cart", "purchase", "remove_from_cart"};
    std::vector<std::string> regions = {"US-East", "US-West", "EU", "Asia"};
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> userDist(1, 50000);
    std::uniform_int_distribution<> productDist(1, 10000);
    std::uniform_int_distribution<> categoryDist(0, categories.size() - 1);
    std::uniform_int_distribution<> actionDist(0, actions.size() - 1);
    std::uniform_int_distribution<> regionDist(0, regions.size() - 1);
    std::uniform_int_distribution<> sessionDist(1, 100000);
    std::uniform_int_distribution<> quantityDist(1, 5);
    std::uniform_int_distribution<> timeDist(0, 7 * 24 * 3600); // Last 7 days in seconds
    std::uniform_real_distribution<> priceDist(10.0, 1000.0);
    std::uniform_int_distribution<> boolDist(0, 1);
    
    for (int i = 0; i < numRecords; i++) {
        SampleRecord record;
        record.userId = "user_" + std::to_string(userDist(gen));
        record.productId = "prod_" + std::to_string(productDist(gen));
        record.category = categories[categoryDist(gen)];
        record.action = actions[actionDist(gen)];
        record.sessionId = "session_" + std::to_string(sessionDist(gen));
        record.quantity = quantityDist(gen);
        record.price = std::round(priceDist(gen) * 100.0) / 100.0;
        record.isPremium = boolDist(gen) == 1;
        record.region = regions[regionDist(gen)];
        
        // Generate timestamp (current time minus random seconds)
        auto now = std::chrono::system_clock::now();
        auto timestamp = now - std::chrono::seconds(timeDist(gen));
        auto time_t = std::chrono::system_clock::to_time_t(timestamp);
        
        std::ostringstream oss;
        oss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
        record.timestamp = oss.str();
        
        data.push_back(record);
        
        if ((i + 1) % 5000 == 0) {
            LOG_INFO("   Generated " + std::to_string(i + 1) + " records...");
        }
    }
    
    LOG_INFO("✅ Generated " + std::to_string(data.size()) + " records");
    return data;
}

void saveSampleDataToCSV(const std::vector<SampleRecord>& data, const std::string& filename) {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw SparkException("Cannot open file for writing: " + filename);
    }
    
    // Write header
    file << "user_id,product_id,category,action,timestamp,price,quantity,session_id,is_premium,region\n";
    
    // Write data
    for (const auto& record : data) {
        file << record.toCSV() << "\n";
    }
    
    file.close();
    LOG_INFO("✅ Saved " + std::to_string(data.size()) + " records to CSV: " + filename);
}

void saveSampleDataToJSON(const std::vector<SampleRecord>& data, const std::string& filename) {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw SparkException("Cannot open file for writing: " + filename);
    }
    
    file << "[\n";
    for (size_t i = 0; i < data.size(); i++) {
        file << "  " << data[i].toJSON();
        if (i < data.size() - 1) {
            file << ",";
        }
        file << "\n";
    }
    file << "]\n";
    
    file.close();
    LOG_INFO("✅ Saved " + std::to_string(data.size()) + " records to JSON: " + filename);
}

int executeSparkJob(const SparkConfig& config, const std::string& pythonScript, 
                   const std::vector<std::string>& args) {
    LOG_INFO("🚀 Executing Spark job: " + pythonScript);
    
    std::ostringstream command;
    command << "spark-submit"
            << " --master " << config.master
            << " --conf spark.executor.memory=" << config.executorMemory
            << " --conf spark.executor.cores=" << config.executorCores
            << " --conf spark.driver.memory=" << config.driverMemory
            << " --conf spark.app.name=" << config.appName
            << " " << pythonScript;
    
    // Add additional arguments
    for (const auto& arg : args) {
        command << " " << arg;
    }
    
    std::string cmdStr = command.str();
    LOG_INFO("Command: " + cmdStr);
    
    int result = std::system(cmdStr.c_str());
    
    if (result == 0) {
        LOG_INFO("✅ Spark job completed successfully");
    } else {
        LOG_ERROR("❌ Spark job failed with exit code: " + std::to_string(result));
    }
    
    return result;
}

void printPerformanceMetrics(const PerformanceMetrics& metrics) {
    std::cout << "\n📊 " << metrics.operationName << " Performance Metrics:\n";
    std::cout << "   Duration: " << std::fixed << std::setprecision(2) 
              << metrics.getDurationSeconds() << " seconds\n";
    
    if (metrics.recordsProcessed > 0) {
        std::cout << "   Records Processed: " << metrics.recordsProcessed << "\n";
        std::cout << "   Records per Second: " << std::fixed << std::setprecision(0) 
                  << metrics.getRecordsPerSecond() << "\n";
    }
}

bool createDirectory(const std::string& path) {
    struct stat st;
    if (stat(path.c_str(), &st) == 0) {
        return S_ISDIR(st.st_mode);
    }
    
    // Try to create directory
    int result = mkdir(path.c_str(), 0755);
    if (result == 0) {
        LOG_INFO("✅ Created directory: " + path);
        return true;
    } else {
        LOG_WARN("⚠️  Could not create directory: " + path);
        return false;
    }
}

std::string getCurrentTimestamp(const std::string& format) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&time_t), format.c_str());
    return oss.str();
}

int executeCommand(const std::string& command, std::string& output) {
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) {
        throw SparkException("Failed to execute command: " + command);
    }
    
    char buffer[128];
    std::ostringstream oss;
    
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        oss << buffer;
    }
    
    output = oss.str();
    int result = pclose(pipe);
    
    return WEXITSTATUS(result);
}

bool checkSparkCluster(const std::string& master) {
    LOG_INFO("🔄 Checking Spark cluster connectivity...");
    
    // Extract host and port from master URL
    std::string host = "192.168.1.184";
    std::string port = "7077";
    
    if (master.find("spark://") == 0) {
        std::string hostPort = master.substr(8); // Remove "spark://"
        size_t colonPos = hostPort.find(':');
        if (colonPos != std::string::npos) {
            host = hostPort.substr(0, colonPos);
            port = hostPort.substr(colonPos + 1);
        }
    }
    
    std::string command = "nc -z " + host + " " + port + " 2>/dev/null";
    std::string output;
    int result = executeCommand(command, output);
    
    if (result == 0) {
        LOG_INFO("✅ Spark cluster is accessible");
        return true;
    } else {
        LOG_WARN("⚠️  Cannot connect to Spark cluster: " + master);
        return false;
    }
}

void printDataQualitySummary(const std::vector<SampleRecord>& data) {
    std::cout << "\n📊 Data Quality Summary:\n";
    std::cout << "   Total Records: " << data.size() << "\n";
    
    // Category distribution
    std::map<std::string, int> categoryCount;
    std::map<std::string, int> actionCount;
    std::map<std::string, int> regionCount;
    
    std::vector<double> prices;
    std::vector<int> quantities;
    int premiumCount = 0;
    
    for (const auto& record : data) {
        categoryCount[record.category]++;
        actionCount[record.action]++;
        regionCount[record.region]++;
        prices.push_back(record.price);
        quantities.push_back(record.quantity);
        if (record.isPremium) premiumCount++;
    }
    
    std::cout << "\n   Category Distribution:\n";
    for (const auto& pair : categoryCount) {
        double percentage = (double)pair.second / data.size() * 100;
        std::cout << "     " << pair.first << ": " << pair.second 
                  << " (" << std::fixed << std::setprecision(1) << percentage << "%)\n";
    }
    
    std::cout << "\n   Action Distribution:\n";
    for (const auto& pair : actionCount) {
        double percentage = (double)pair.second / data.size() * 100;
        std::cout << "     " << pair.first << ": " << pair.second 
                  << " (" << std::fixed << std::setprecision(1) << percentage << "%)\n";
    }
    
    // Price statistics
    auto priceStats = calculateStatistics(prices);
    std::cout << "\n   Price Statistics:\n";
    std::cout << "     Mean: $" << std::fixed << std::setprecision(2) << priceStats["mean"] << "\n";
    std::cout << "     Min: $" << std::fixed << std::setprecision(2) << priceStats["min"] << "\n";
    std::cout << "     Max: $" << std::fixed << std::setprecision(2) << priceStats["max"] << "\n";
    std::cout << "     Std Dev: $" << std::fixed << std::setprecision(2) << priceStats["stddev"] << "\n";
    
    std::cout << "\n   Premium Users: " << premiumCount 
              << " (" << std::fixed << std::setprecision(1) 
              << (double)premiumCount / data.size() * 100 << "%)\n";
}

std::map<std::string, double> calculateStatistics(const std::vector<double>& values) {
    std::map<std::string, double> stats;
    
    if (values.empty()) {
        return stats;
    }
    
    // Calculate mean
    double sum = 0;
    for (double value : values) {
        sum += value;
    }
    double mean = sum / values.size();
    stats["mean"] = mean;
    
    // Find min and max
    double minVal = *std::min_element(values.begin(), values.end());
    double maxVal = *std::max_element(values.begin(), values.end());
    stats["min"] = minVal;
    stats["max"] = maxVal;
    
    // Calculate standard deviation
    double variance = 0;
    for (double value : values) {
        variance += (value - mean) * (value - mean);
    }
    variance /= values.size();
    stats["stddev"] = std::sqrt(variance);
    
    return stats;
}

void log(const std::string& level, const std::string& message) {
    std::string timestamp = getCurrentTimestamp("%Y-%m-%d %H:%M:%S");
    std::cout << "[" << timestamp << "] " << level << ": " << message << std::endl;
}

} // namespace SparkCommon
