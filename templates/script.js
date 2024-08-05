const socket = io();
const alertLevelElement = document.getElementById('alert-level');
const MAX_HISTORY_SECONDS = 20;

socket.on('connect', function() {
    console.log('WebSocket connected');
});


function fetchServerTime(callback) {
    fetch('/api/server_time')
        .then(response => response.json())
        .then(data => {
            const serverTime = new Date(data.time);
            callback(serverTime);
        })
        .catch(error => console.error('Error fetching server time:', error));
}

let lastFrameTime = null;

// Formatieren des Datums
const options = {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false // 24-Stunden-Format
};

socket.on('frame', function(data) {
    // Serverzeit abrufen und dann den Frame verarbeiten
    fetchServerTime(function(serverTime) {
        const frameTime = new Date(data.time); // Zeit des empfangenen Frames
        const timeDiff = (serverTime - frameTime) / 1000; // Zeitdifferenz in Sekunden
        const formattedDate = frameTime.toLocaleString('de-DE', options); // 'de-DE' für deutsches Format

        if (data.data) {
            const videoElement = document.getElementById('video');
            videoElement.src = 'data:image/jpeg;base64,' + data.data;
            videoElement.style.width = '100%';
            videoElement.style.height = 'auto';
        }

        lastFrameTime = frameTime;


        // Lag-Anzeige immer aktualisieren
        document.getElementById('lagDisplay').innerText = formattedDate + ' Δ' + timeDiff.toFixed(2) + 's';

        const response = {
            diff: timeDiff,
            serverTime: serverTime
        };
        socket.emit('time_diff', response);
    });
});

// AUDIO

socket.on('alert', function(data) {
    const alert_ratio_audio = data.audio;
    const alert_ratio_video = data.video;

    let color = 'black';

    if (data.alert) {
        color = 'red';
        playAlertAudio();
    } else if (alert_ratio_audio > 0.2 || alert_ratio_video > 0.065) {
        color = 'orange';
    }

    // Aktualisiere die Text- und Hintergrundfarbe des Alert-Level-Elements
    alertLevelElement.textContent = 'Alert Level: A:' + alert_ratio_audio.toFixed(2) + ', V:'  + alert_ratio_video.toFixed(2);
    alertLevelElement.style.color = color;
});

let alertFile = new Audio("{{ url_for('static', filename='alert.mp3') }}");
let isPlaying = false;

// Funktion zum Abspielen der Audio-Datei
function playAlertAudio() {
    if (!isPlaying) {
        isPlaying = true;
        alertFile.play()
            .then(() => {
                alertFile.onended = () => {
                    isPlaying = false;
                };
            })
            .catch(error => {
                console.error('Fehler beim Abspielen der Audio-Datei:', error);
                alert('Berechtigungen für Alarmknopf setzen');
                setTimeout(() => {
                    isPlaying = false;
                }, 3000);
            });
    }
}

socket.on('disconnect', function() {
    console.log('WebSocket disconnected');
});

// THRESHOLD SETZEN
async function fetchThreshold() {
    const response = await fetch('/api/get_audio_threshold');
    const data = await response.json();
    const threshold = data.threshold;
    document.getElementById('thresholdSlider').value = threshold;
    document.getElementById('thresholdValue').innerText = threshold;
}

async function setThreshold(value) {
    const response = await fetch('/api/set_audio_threshold', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ threshold: parseFloat(value) }),
    });
    const data = await response.json();
    console.log(data.message);
}

function onSliderChange(event) {
    const value = event.target.value;
    document.getElementById('thresholdValue').innerText = value;
    setThreshold(value);
}

window.onload = fetchThreshold;

// DOM

document.addEventListener('DOMContentLoaded', function() {
    const baselinebutton = document.getElementById('setBaselineButton');
    const playButton = document.getElementById('playButton');

    baselinebutton.addEventListener('click', function() {
        // Button deaktivieren und ausgrauen
        baselinebutton.disabled = true;
        baselinebutton.style.opacity = 0.5;

        fetch('/api/set_baseline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
        })
        .catch(error => {
        })
        .finally(() => {
            baselinebutton.disabled = false;
            baselinebutton.style.opacity = 1.0;
        });
    });

    // Funktion zum Umschalten des Alarms
    playButton.addEventListener('click', function() {
        fetch('/api/alert_toggle')
            .then(response => response.json())
            .then(data => {
                updateButton(data.status);
            })
            .catch(error => console.error('Fehler beim Umschalten des Alarms:', error));
    });

    // Funktion zum Laden des Alarmstatus
    function loadAlertStatus() {
        fetch('/api/alert_is_enabled')
            .then(response => response.json())
            .then(data => {
                updateButton(data.status);
            })
            .catch(error => console.error('Fehler beim Laden des Alarmstatus:', error));
    }

    // Funktion zum Aktualisieren des Buttons basierend auf dem Status
    function updateButton(isEnabled) {
        if (isEnabled) {
            playButton.textContent = 'Alarm an';
            playAlertAudio();
        } else {
            playButton.textContent = 'Alarm aus';
        }
    }

    loadAlertStatus();
});