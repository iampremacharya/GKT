document.querySelector(".cta").addEventListener("click", () => {
    alert("Welcome! Let's get started on your journey.");
});

document.getElementById("mobile-menu").addEventListener("click", () => {
    const navMenu = document.querySelector(".nav-menu");
    navMenu.classList.toggle("active");
});

document.getElementById("contact-form").addEventListener("submit", (e) => {
    e.preventDefault();
    alert("Message sent!");
});
const mobileMenu = document.getElementById('mobile-menu');
const navMenu = document.querySelector('.nav-menu');

mobileMenu.addEventListener('click', () => {
    navMenu.classList.toggle('active');
});
