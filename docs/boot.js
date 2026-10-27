// If the main script can't run in this browser, say so on the page instead of doing nothing.
function showProblem(text) {
  var el = document.getElementById("problem");
  if (el) { el.textContent = text; el.hidden = false; }
}
window.addEventListener("error", function (e) { showProblem("Jarvis hit an error: " + (e.message || "unknown") + ". Screenshot this and send it."); });
setTimeout(function () {
  if (!window.jarvisReady) showProblem("Jarvis couldn't start in this browser, so typing and saving won't work. Update the device (Settings > General > Software Update) or open the page in Safari or Chrome. Browser: " + navigator.userAgent);
}, 4000);
