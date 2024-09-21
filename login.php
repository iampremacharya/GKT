<?php
session_start();
include('config.php'); // A file to connect to the database

// Retrieve login form data
$username = $_POST['username'];
$password = $_POST['password'];

// Check if username exists in the database
$query = $pdo->prepare('SELECT * FROM users WHERE username = :username');
$query->bindParam(':username', $username);
$query->execute();

$user = $query->fetch(PDO::FETCH_ASSOC);

if ($user) {
    // Verify password using password_verify
    if (password_verify($password, $user['password'])) {
        $_SESSION['username'] = $user['username']; // Start a session for the logged-in user
        echo "Login successful! Welcome " . $_SESSION['username'];
        // Redirect to another page if login is successful
        header('Location: dashboard.php');
    } else {
        echo "Invalid password.";
    }
} else {
    echo "Username not found.";
}
?>
