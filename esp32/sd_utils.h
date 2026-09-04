"""SD Card Utilities for ESP32 Flashcard Reader.

Provides functions for:
- Reading files from SD card
- Decompressing gzip files
- JSON parsing
- Efficient memory management for large files
"""

#ifndef SD_UTILS_H
#define SD_UTILS_H

#include <Arduino.h>
#include <SD.h>
#include <ArduinoJson.h>

// Configuration
#define SD_CS_PIN 5          // Chip select pin for SPI
#define MAX_FILENAME_LEN 255
#define BUFFER_SIZE 1024     // Read buffer size
#define JSON_BUFFER_SIZE 8192 // JSON document buffer

/**
 * Initialize SD card interface.
 * 
 * @return true if initialization successful, false otherwise
 */
bool initSD() {
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("SD Card initialization failed!");
    return false;
  }
  
  Serial.println("SD Card initialized successfully");
  
  // List root directory
  File root = SD.open("/");
  if (root) {
    Serial.println("Root directory contents:");
    listDir(root);
    root.close();
  }
  
  return true;
}

/**
 * List directory contents.
 * 
 * @param dir Directory to list
 * @param indent Indentation level
 */
void listDir(File dir, int indent = 0) {
  while (true) {
    File entry = dir.openNextFile();
    if (!entry) break;
    
    for (int i = 0; i < indent; i++) Serial.print(" ");
    Serial.print(entry.name());
    
    if (entry.isDirectory()) {
      Serial.println("/");
      listDir(entry, indent + 2);
    } else {
      Serial.print(" - ");
      Serial.print(entry.size());
      Serial.println(" bytes");
    }
    
    entry.close();
  }
}

/**
 * Check if file exists on SD card.
 * 
 * @param filename Path to file
 * @return true if file exists
 */
bool fileExists(const char* filename) {
  return SD.exists(filename);
}

/**
 * Get file size.
 * 
 * @param filename Path to file
 * @return File size in bytes, or 0 if file not found
 */
size_t getFileSize(const char* filename) {
  File file = SD.open(filename, FILE_READ);
  if (!file) return 0;
  
  size_t size = file.size();
  file.close();
  return size;
}

/**
 * Read entire file into string (use for small files only).
 * 
 * @param filename Path to file
 * @return File contents as string, empty string if error
 */
String readFileToString(const char* filename) {
  File file = SD.open(filename, FILE_READ);
  if (!file) {
    Serial.print("Error opening file: ");
    Serial.println(filename);
    return "";
  }
  
  String content = "";
  while (file.available()) {
    char c = file.read();
    content += c;
  }
  
  file.close();
  return content;
}

/**
 * Read file in chunks (for large files).
 * Calls callback function for each chunk.
 * 
 * @param filename Path to file
 * @param callback Function to call with each chunk (char* data, size_t len)
 * @return Number of bytes read, or -1 on error
 */
size_t readFileInChunks(const char* filename, 
                        void (*callback)(const char*, size_t)) {
  File file = SD.open(filename, FILE_READ);
  if (!file) {
    Serial.print("Error opening file: ");
    Serial.println(filename);
    return -1;
  }
  
  char buffer[BUFFER_SIZE];
  size_t totalRead = 0;
  
  while (file.available()) {
    size_t bytesRead = file.read((uint8_t*)buffer, BUFFER_SIZE);
    if (bytesRead > 0) {
      callback(buffer, bytesRead);
      totalRead += bytesRead;
    }
  }
  
  file.close();
  return totalRead;
}

/**
 * Parse JSON file from SD card.
 * 
 * @param filename Path to JSON file
 * @param doc Reference to JsonDocument to populate
 * @return true if successful
 */
bool readJsonFile(const char* filename, JsonDocument& doc) {
  File file = SD.open(filename, FILE_READ);
  if (!file) {
    Serial.print("Error opening JSON file: ");
    Serial.println(filename);
    return false;
  }
  
  DeserializationError error = deserializeJson(doc, file);
  file.close();
  
  if (error) {
    Serial.print("Error parsing JSON: ");
    Serial.println(error.c_str());
    return false;
  }
  
  return true;
}

/**
 * Write JSON document to SD card.
 * 
 * @param filename Path to output file
 * @param doc JsonDocument to write
 * @return true if successful
 */
bool writeJsonFile(const char* filename, const JsonDocument& doc) {
  File file = SD.open(filename, FILE_WRITE);
  if (!file) {
    Serial.print("Error opening file for writing: ");
    Serial.println(filename);
    return false;
  }
  
  size_t bytesWritten = serializeJson(doc, file);
  file.close();
  
  return bytesWritten > 0;
}

/**
 * Simple gzip decompression (requires minimal decompression).
 * For use with small gzipped flashcard files.
 * 
 * Note: This is a simplified version. For production use,
 * consider using a dedicated decompression library.
 * 
 * @param compressedData Pointer to compressed data
 * @param compressedSize Size of compressed data
 * @param decompressedBuffer Buffer for decompressed output
 * @param bufferSize Size of output buffer
 * @return Size of decompressed data, or -1 on error
 */
int decompressGzip(const uint8_t* compressedData, size_t compressedSize,
                   uint8_t* decompressedBuffer, size_t bufferSize) {
  // Check gzip magic number
  if (compressedSize < 10 || compressedData[0] != 0x1f || compressedData[1] != 0x8b) {
    Serial.println("Invalid gzip header");
    return -1;
  }
  
  // Note: Actual decompression requires zlib or similar
  // This is a placeholder - for ESP32, consider using:
  // - TinyDeflate library
  // - Compressed JSON instead of gzip
  // - Store uncompressed if space permits
  
  Serial.println("Warning: Gzip decompression not fully implemented");
  Serial.println("Consider storing uncompressed JSON or using TinyDeflate library");
  
  return -1;
}

/**
 * Search for a term in flashcards file.
 * Returns matching flashcard entries.
 * 
 * @param filename Path to flashcards JSON file
 * @param searchTerm Term to search for
 * @param results Array to store results
 * @param maxResults Maximum number of results to return
 * @return Number of results found
 */
int searchFlashcards(const char* filename, const char* searchTerm,
                     JsonArray& results, int maxResults = 10) {
  StaticJsonDocument<JSON_BUFFER_SIZE> doc;
  
  if (!readJsonFile(filename, doc)) {
    return -1;
  }
  
  JsonArray cards = doc["flashcards"].as<JsonArray>();
  int found = 0;
  
  String search(searchTerm);
  search.toLowerCase();
  
  for (JsonObject card : cards) {
    if (found >= maxResults) break;
    
    String question = card["question"].as<String>();
    String answer = card["answer"].as<String>();
    
    question.toLowerCase();
    answer.toLowerCase();
    
    if (question.indexOf(search) >= 0 || answer.indexOf(search) >= 0) {
      results.add(card);
      found++;
    }
  }
  
  return found;
}

/**
 * Get flashcard by ID.
 * 
 * @param filename Path to flashcards JSON file
 * @param cardId ID of card to retrieve
 * @param result JsonObject to populate
 * @return true if card found
 */
bool getFlashcardById(const char* filename, const char* cardId, JsonObject& result) {
  StaticJsonDocument<JSON_BUFFER_SIZE> doc;
  
  if (!readJsonFile(filename, doc)) {
    return false;
  }
  
  JsonArray cards = doc["flashcards"].as<JsonArray>();
  
  for (JsonObject card : cards) {
    if (card["id"].as<String>() == cardId) {
      result = card;
      return true;
    }
  }
  
  return false;
}

/**
 * Get all flashcards for a category.
 * 
 * @param filename Path to flashcards JSON file
 * @param category Category to filter by
 * @param results Array to populate
 * @param maxResults Maximum results to return
 * @return Number of results
 */
int getFlashcardsByCategory(const char* filename, const char* category,
                            JsonArray& results, int maxResults = 20) {
  StaticJsonDocument<JSON_BUFFER_SIZE> doc;
  
  if (!readJsonFile(filename, doc)) {
    return -1;
  }
  
  JsonArray cards = doc["flashcards"].as<JsonArray>();
  int found = 0;
  
  for (JsonObject card : cards) {
    if (found >= maxResults) break;
    
    if (card["category"].as<String>() == category) {
      results.add(card);
      found++;
    }
  }
  
  return found;
}

/**
 * Print flashcard to serial.
 * 
 * @param card JsonObject containing flashcard data
 */
void printFlashcard(const JsonObject& card) {
  Serial.println("\n--- Flashcard ---");
  Serial.print("ID: ");
  Serial.println(card["id"].as<String>());
  Serial.print("Q: ");
  Serial.println(card["question"].as<String>());
  Serial.print("A: ");
  Serial.println(card["answer"].as<String>());
  Serial.print("Category: ");
  Serial.println(card["category"].as<String>());
  Serial.print("Difficulty: ");
  Serial.println(card["difficulty"].as<String>());
}

#endif // SD_UTILS_H
