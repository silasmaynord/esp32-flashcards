/**
 * ESP32 Flashcard Reader
 * 
 * Reads flashcards from SD card and provides simple lookup interface.
 * Uses serial communication for queries and display.
 * 
 * Hardware:
 * - ESP32 development board
 * - SD card module (SPI interface)
 * - USB serial for communication
 * 
 * SD Card pinout (SPI mode):
 * - CS (Chip Select): GPIO 5
 * - MOSI (MOSI): GPIO 23
 * - MISO (MISO): GPIO 19
 * - SCK (Clock): GPIO 18
 * 
 * File structure on SD card:
 * /flashcards/
 *   ├── cards.json        (uncompressed flashcards)
 *   └── cards.json.gz     (compressed - requires decompression)
 */

#include <Arduino.h>
#include <SD.h>
#include <SPI.h>
#include <ArduinoJson.h>
#include "sd_utils.h"

// Configuration
#define SERIAL_BAUD 115200
#define FLASHCARD_FILE "/flashcards/cards.json"
#define MAX_SEARCH_RESULTS 5

// Global variables
StaticJsonDocument<JSON_BUFFER_SIZE> flashcardDoc;
bool sdInitialized = false;
bool flashcardsLoaded = false;

// Function prototypes
void handleSerialInput();
void displayMainMenu();
void searchCards();
void browseByCategoryMenu();
void getRandomCard();
void displayFlashcard(const JsonObject& card);
void printSystemInfo();

/**
 * Setup function - runs once at startup
 */
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(2000);  // Wait for serial to stabilize
  
  Serial.println("\n\n========================================");
  Serial.println("ESP32 Flashcard Reader - Starting");
  Serial.println("========================================\n");
  
  // Initialize SD card
  Serial.println("[1] Initializing SD Card...");
  sdInitialized = initSD();
  
  if (!sdInitialized) {
    Serial.println("ERROR: Failed to initialize SD card!");
    Serial.println("Check connections and try again.");
    return;
  }
  
  // Load flashcards
  Serial.print("\n[2] Loading flashcards from ");
  Serial.println(FLASHCARD_FILE);
  
  if (!fileExists(FLASHCARD_FILE)) {
    Serial.println("ERROR: Flashcard file not found!");
    Serial.print("Expected: ");
    Serial.println(FLASHCARD_FILE);
    return;
  }
  
  if (readJsonFile(FLASHCARD_FILE, flashcardDoc)) {
    flashcardsLoaded = true;
    JsonObject metadata = flashcardDoc["metadata"];
    
    Serial.println("\n========== Flashcard Metadata ==========");
    Serial.print("Book: ");
    Serial.println(metadata["book_title"].as<String>());
    Serial.print("Author: ");
    Serial.println(metadata["book_author"].as<String>());
    Serial.print("Total Cards: ");
    Serial.println(metadata["total_cards"].as<int>());
    Serial.print("Language: ");
    Serial.println(metadata["book_language"].as<String>());
    
    JsonArray categories = metadata["categories"];
    Serial.print("Categories: ");
    bool first = true;
    for (const String& cat : categories) {
      if (!first) Serial.print(", ");
      Serial.print(cat);
      first = false;
    }
    Serial.println("\n========================================\n");
  } else {
    Serial.println("ERROR: Failed to parse flashcard file!");
    return;
  }
  
  Serial.println("[3] Initialization complete!\n");
  displayMainMenu();
}

/**
 * Main loop - continuously handle serial input
 */
void loop() {
  if (Serial.available()) {
    handleSerialInput();
  }
  delay(100);
}

/**
 * Handle incoming serial commands
 */
void handleSerialInput() {
  String input = Serial.readStringUntil('\n');
  input.trim();
  input.toLowerCase();
  
  if (input.isEmpty()) {
    return;
  }
  
  Serial.print("\n> ");
  Serial.println(input);
  Serial.println();
  
  // Parse command
  if (input == "menu" || input == "m") {
    displayMainMenu();
  }
  else if (input == "search" || input == "s") {
    searchCards();
  }
  else if (input == "browse" || input == "b") {
    browseByCategoryMenu();
  }
  else if (input == "random" || input == "r") {
    getRandomCard();
  }
  else if (input == "info" || input == "i") {
    printSystemInfo();
  }
  else if (input == "help" || input == "h") {
    displayMainMenu();
  }
  else if (input == "stats" || input == "st") {
    displayStatistics();
  }
  else {
    Serial.println("Unknown command. Type 'menu' or 'help' for options.");
  }
}

/**
 * Display main menu
 */
void displayMainMenu() {
  if (!flashcardsLoaded) {
    Serial.println("ERROR: Flashcards not loaded. Check SD card and restart.");
    return;
  }
  
  Serial.println("========= FLASHCARD MENU ==========");
  Serial.println("Commands:");
  Serial.println("  search (s)     - Search for cards by keyword");
  Serial.println("  browse (b)     - Browse by category");
  Serial.println("  random (r)     - Get random flashcard");
  Serial.println("  stats (st)     - View statistics");
  Serial.println("  info (i)       - System information");
  Serial.println("  menu (m)       - Show this menu");
  Serial.println("  help (h)       - Show this menu");
  Serial.println("==================================\n");
}

/**
 * Search for flashcards by keyword
 */
void searchCards() {
  Serial.println("Enter search term (or 'back' to return):");
  
  while (!Serial.available()) {
    delay(100);
  }
  
  String searchTerm = Serial.readStringUntil('\n');
  searchTerm.trim();
  
  if (searchTerm.toLowerCase() == "back") {
    return;
  }
  
  if (searchTerm.isEmpty()) {
    Serial.println("Search term cannot be empty.");
    return;
  }
  
  Serial.print("\nSearching for: ");
  Serial.println(searchTerm);
  Serial.println();
  
  // Search in flashcards
  JsonArray cards = flashcardDoc["flashcards"];
  int found = 0;
  
  String search = searchTerm;
  search.toLowerCase();
  
  for (JsonObject card : cards) {
    if (found >= MAX_SEARCH_RESULTS) {
      Serial.print("\n(Showing first ");
      Serial.print(MAX_SEARCH_RESULTS);
      Serial.println(" results)\n");
      break;
    }
    
    String question = card["question"].as<String>();
    String answer = card["answer"].as<String>();
    
    question.toLowerCase();
    answer.toLowerCase();
    
    if (question.indexOf(search) >= 0 || answer.indexOf(search) >= 0) {
      displayFlashcard(card);
      found++;
    }
  }
  
  if (found == 0) {
    Serial.println("No flashcards found matching that term.");
  } else {
    Serial.print("\nFound ");
    Serial.print(found);
    Serial.println(" matching card(s).");
  }
  Serial.println();
}

/**
 * Browse flashcards by category
 */
void browseByCategoryMenu() {
  JsonObject metadata = flashcardDoc["metadata"];
  JsonArray categories = metadata["categories"];
  
  Serial.println("\nAvailable categories:");
  
  int index = 0;
  for (const String& cat : categories) {
    Serial.print("  ");
    Serial.print(index);
    Serial.print(". ");
    Serial.println(cat);
    index++;
  }
  
  Serial.println("\nEnter category number (or 'back'):");
  
  while (!Serial.available()) {
    delay(100);
  }
  
  String input = Serial.readStringUntil('\n');
  input.trim();
  
  if (input.toLowerCase() == "back") {
    return;
  }
  
  int catIndex = input.toInt();
  
  if (catIndex < 0 || catIndex >= categories.size()) {
    Serial.println("Invalid category number.");
    return;
  }
  
  String selectedCategory = categories[catIndex].as<String>();
  
  Serial.print("\nShowing cards for category: ");
  Serial.println(selectedCategory);
  Serial.println();
  
  // Get cards for this category
  JsonArray cards = flashcardDoc["flashcards"];
  int shown = 0;
  
  for (JsonObject card : cards) {
    if (shown >= 10) {  // Limit to 10 per category
      Serial.println("(Showing first 10 cards)\n");
      break;
    }
    
    if (card["category"].as<String>() == selectedCategory) {
      displayFlashcard(card);
      shown++;
    }
  }
  
  if (shown == 0) {
    Serial.println("No cards found in this category.");
  }
  Serial.println();
}

/**
 * Display a random flashcard
 */
void getRandomCard() {
  JsonArray cards = flashcardDoc["flashcards"];
  
  if (cards.size() == 0) {
    Serial.println("No flashcards available.");
    return;
  }
  
  int randomIndex = random(0, cards.size());
  JsonObject card = cards[randomIndex];
  
  Serial.println("Random flashcard:");
  displayFlashcard(card);
}

/**
 * Display a single flashcard
 */
void displayFlashcard(const JsonObject& card) {
  Serial.println("----------------------------");
  
  Serial.print("Q: ");
  Serial.println(card["question"].as<String>());
  
  Serial.println();
  
  Serial.print("A: ");
  Serial.println(card["answer"].as<String>());
  
  Serial.print("\n[Category: ");
  Serial.print(card["category"].as<String>());
  Serial.print(" | Difficulty: ");
  Serial.print(card["difficulty"].as<String>());
  Serial.println("]");
  
  Serial.println("----------------------------\n");
}

/**
 * Display system information
 */
void printSystemInfo() {
  Serial.println("\n========= SYSTEM INFO ==========");
  
  Serial.print("ESP32 Chip ID: ");
  Serial.println((uint16_t)(ESP.getEfuseMac() >> 32), HEX);
  
  Serial.print("Free Heap: ");
  Serial.print(ESP.getFreeHeap());
  Serial.println(" bytes");
  
  Serial.print("Total Heap: ");
  Serial.print(ESP.getHeapSize());
  Serial.println(" bytes");
  
  Serial.print("Largest Free Block: ");
  Serial.print(ESP.getMaxAllocHeap());
  Serial.println(" bytes");
  
  Serial.print("CPU Frequency: ");
  Serial.print(getCpuFrequencyMhz());
  Serial.println(" MHz");
  
  if (sdInitialized && flashcardsLoaded) {
    Serial.print("\nFlashcard File: ");
    Serial.print(FLASHCARD_FILE);
    Serial.print(" (");
    Serial.print(getFileSize(FLASHCARD_FILE));
    Serial.println(" bytes)");
    
    JsonObject metadata = flashcardDoc["metadata"];
    Serial.print("Total Cards Loaded: ");
    Serial.println(metadata["total_cards"].as<int>());
  } else {
    Serial.println("\nSD/Flashcards: NOT INITIALIZED");
  }
  
  Serial.println("================================\n");
}

/**
 * Display flashcard statistics
 */
void displayStatistics() {
  if (!flashcardsLoaded) {
    Serial.println("Flashcards not loaded.");
    return;
  }
  
  JsonObject metadata = flashcardDoc["metadata"];
  JsonArray cards = flashcardDoc["flashcards"];
  
  Serial.println("\n========= STATISTICS ==========");
  
  // Count by difficulty
  int easyCount = 0, mediumCount = 0, hardCount = 0;
  for (JsonObject card : cards) {
    String difficulty = card["difficulty"].as<String>();
    if (difficulty == "easy") easyCount++;
    else if (difficulty == "medium") mediumCount++;
    else if (difficulty == "hard") hardCount++;
  }
  
  Serial.print("Total Cards: ");
  Serial.println(metadata["total_cards"].as<int>());
  
  Serial.print("By Difficulty:\n");
  Serial.print("  Easy: ");
  Serial.println(easyCount);
  Serial.print("  Medium: ");
  Serial.println(mediumCount);
  Serial.print("  Hard: ");
  Serial.println(hardCount);
  
  // Average lengths
  long totalQLen = 0, totalALen = 0;
  for (JsonObject card : cards) {
    totalQLen += card["question"].as<String>().length();
    totalALen += card["answer"].as<String>().length();
  }
  
  Serial.print("\nAverage Question Length: ");
  Serial.print(totalQLen / cards.size());
  Serial.println(" chars");
  
  Serial.print("Average Answer Length: ");
  Serial.print(totalALen / cards.size());
  Serial.println(" chars");
  
  Serial.println("===============================\n");
}
