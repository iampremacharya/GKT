<?php
// Database connection
$host = 'localhost';
$db = 'my_database';
$user = 'root'; // Update with your MySQL username
$pass = '9744319864'; // Update with your MySQL password

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

$sql = "SELECT * FROM users";
$result = $conn->query($sql);

if ($result->num_rows > 0) {
    echo "<h1>Registered Users</h1>";
    echo "<table border='1'><tr><th>ID</th><th>Username</th><th>Email</th></tr>";
    while ($row = $result->fetch_assoc()) {
        echo "<tr><td>{$row['id']}</td><td>{$row['username']}</td><td>{$row['email']}</td></tr>";
    }
    echo "</table>";
} else {
    echo "No users found.";
}
$conn->close();
