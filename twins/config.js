/*
 * Production configuration for Find Your 7 Twins.
 *
 * Set API_BASE to the HTTPS URL of the deployed FastAPI service.
 * Leave it empty only when the API is reverse-proxied under the same origin.
 */
window.TWINS_CONFIG = Object.freeze({
    API_BASE: "https://find-your-7-twins-api.onrender.com"
});
