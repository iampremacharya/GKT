<?php
// Include database connection (config.php)
include('config.php');

// Check if form data has been submitted
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    
    // Get the username and password from the form
    $username = $_POST['username'];
    $password = $_POST['password'];

    // Hash the password using bcrypt
    $hashed_password = password_hash($password, PASSWORD_BCRYPT);

    // Insert the username and hashed password into the database
    try {
        $query = $pdo->prepare('INSERT INTO users (username, password) VALUES (:username, :password)');
        $query->bindParam(':username', $username);
        $query->bindParam(':password', $hashed_password);
        $query->execute();

        echo "Registration successful!";
    } catch (PDOException $e) {
        echo "Error: " . $e->getMessage();
    }
}
?>
