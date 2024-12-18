<?php

// Include Composer autoloader (make sure this is in the same directory as your composer.json)
require 'vendor/autoload.php';

use Stichoza\GoogleTranslate\GoogleTranslate;

// Function to translate text and return translated content
function translateContent($content, $sourceLang = 'en', $targetLang = 'fa') {
    $tr = new GoogleTranslate($targetLang);
    $tr->setSource($sourceLang);  // Translate from source language
    try {
        // Translate content
        return $tr->translate($content);
    } catch (Exception $e) {
        // Handle translation error
        echo "Error translating text: " . $e->getMessage();
        return $content; // Return the original content in case of error
    }
}

// Get input file from command line argument
$inputFile = $argv[1];  // Get the file name from the command line arguments
if (!file_exists($inputFile)) {
    echo "File does not exist.\n";
    exit(1);
}

// Load input JSON file
$jsonContent = file_get_contents($inputFile);
$data = json_decode($jsonContent, true);

if ($data === null) {
    echo "Invalid JSON format.\n";
    exit(1);
}

// Translate the content of each page
foreach ($data['pages'] as &$page) {
    $originalContent = $page['content']['response'];
    echo "Translating page: " . $page['title'] . "\n";

    // Translate the content
    $translatedContent = translateContent($originalContent);

    // Replace the content with the translated version
    $page['content']['response'] = $translatedContent;
}

// Construct the output file path
$parentDir = dirname($inputFile);  // Get the parent directory of the input file
$inputFilename = basename($inputFile);  // Get the filename from the input path

// Create the "fa" subdirectory if it doesn't exist
$outputDir = $parentDir . '/fa';

// Debugging: print out paths to ensure correctness
echo "Parent Directory: $parentDir\n";
echo "Output Directory: $outputDir\n";
echo "Input Filename: $inputFilename\n";

// Check if the "fa" directory exists and create it if not
if (!file_exists($outputDir)) {
    echo "Creating directory: $outputDir\n";  // Debug message for directory creation
    mkdir($outputDir, 0777, true);  // Create the directory, if it doesn't exist
}

// Construct the output file path
$outputFile = $outputDir . '/' . $inputFilename;

// Save the translated JSON to the output file
file_put_contents($outputFile, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

echo "Translation completed and saved to '$outputFile'.\n";