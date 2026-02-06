// UTC Clock
function updateUTCTime() {
    const now = new Date();
    const hours = String(now.getUTCHours()).padStart(2, '0');
    const minutes = String(now.getUTCMinutes()).padStart(2, '0');

    const timeEl = document.getElementById('utc-time');
    if (timeEl) timeEl.textContent = `${hours}:${minutes}`;

    // Update Date
    const options = { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' };
    const dateStr = now.toLocaleDateString('en-GB', options);

    const dateEl = document.getElementById('utc-date');
    if (dateEl) dateEl.textContent = dateStr;
}

setInterval(updateUTCTime, 1000);
// Run immediately on load
document.addEventListener('DOMContentLoaded', updateUTCTime);
