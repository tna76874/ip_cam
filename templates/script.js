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

socket.on('frame', function(data) {
    // Serverzeit abrufen und dann den Frame verarbeiten
    fetchServerTime(function(serverTime) {
        const frameTime = new Date(data.time); // Zeit des empfangenen Frames
        const timeDiff = (serverTime - frameTime) / 1000; // Zeitdifferenz in Sekunden

        document.getElementById('video').src = 'data:image/jpeg;base64,' + data.data;
        lastFrameTime = frameTime; // Aktualisiere den Zeitstempel des letzten Frames

        // Lag-Anzeige immer aktualisieren
        document.getElementById('lagDisplay').innerText = 'Δ' + timeDiff.toFixed(2) + 's';
    });
});

// AUDIO

socket.on('audio', function(data) {
    if (data.history && data.history.length > 0) {
        // Hole den letzten Level-Wert aus der history
        const lastEntry = data.history[data.history.length - 1];
        const currentLevel = lastEntry.level;

        // Bestimme die alert_ratio (hier als Beispiel, wie sie berechnet werden könnte)
        const alert_ratio = data.alert_ratio; // Angenommen, alert_ratio wird direkt aus den Daten übernommen

        // Bestimme die Schriftfarbe basierend auf der alert-Bedingung und alert_ratio
        let color = 'black'; // Default color

        // Bestimme das Vorzeichen von currentLevel
        let sign = '';
        if (currentLevel > 0) {
            sign = '+';
        } else if (currentLevel < 0) {
            sign = '-';
        }

        if (data.alert) { // Überprüfe, ob der Alarm aktiviert ist
            color = 'red'; // Setze die Farbe auf rot, wenn der Alarm aktiv ist
            playAlertAudio(); // Spiele den Alarm ab
        } else if (alert_ratio > 0.2 && alert_ratio < 0.6) {
            color = 'orange'; // Setze orange, wenn alert_ratio zwischen 0.2 und 0.6 liegt
        }

        // Aktualisiere die Text- und Hintergrundfarbe des Alert-Level-Elements
        alertLevelElement.textContent = 'Alert Level: ' + alert_ratio.toFixed(2) + '('  + currentLevel.toFixed(2) + ')';
        alertLevelElement.style.color = color;
    } else {
        // Falls keine history-Daten vorhanden sind
        alertLevelElement.textContent = 'Alert Level: N/A';
        alertLevelElement.style.color = 'black';
    }
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
                alert('Alert');
                isPlaying = false;
            });
    }
}

// // Event-Listener für die Schaltfläche
// document.getElementById('playButton').addEventListener('click', function() {
//     playAlertAudio();
// });

socket.on('disconnect', function() {
    console.log('WebSocket disconnected');
});

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