<?php
// Database connection parameters
$host = 'localhost';         // The server where your database is hosted
$dbname = 'your_database';    // The name of your MySQL database
$user = 'your_db_user';       // Your database username
$pass = 'your_db_password';   // Your database password

try {
    // Create a new PDO instance to connect to the database
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $user, $pass);
    
    // Set error mode to exception, so it throws errors when something goes wrong
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Optional: Set the default fetch mode to fetch associative arrays
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

    // Success message (optional, for testing purposes)
    echo "Database connection successful!";
    
} catch (PDOException $e) {
    // If there is an error connecting to the database, display the error message
    echo "Connection failed: " . $e->getMessage();
}
?>
