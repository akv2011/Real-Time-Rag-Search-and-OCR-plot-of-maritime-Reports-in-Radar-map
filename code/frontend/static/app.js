// frontend/static/app.js
let map = L.map('map').setView([20.0, 68.0], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let radarChartData = [];
let socket = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 5000;
let markers = []; // Array to store markers

function clearAllMarkers() {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
}

function addMarkerToMap(contact) {
    if (contact.latitude && contact.longitude) {
        const marker = L.marker([parseFloat(contact.latitude), parseFloat(contact.longitude)])
            .bindPopup(createPopupContent(contact));
        markers.push(marker);
        marker.addTo(map);
        
        // Center map on the latest marker
        map.setView([contact.latitude, contact.longitude], map.getZoom());
    }
}

function addMarkersToMap(contacts) {
    clearAllMarkers();
    contacts.forEach(contact => {
        if (contact.latitude && contact.longitude) {
            addMarkerToMap(contact);
        }
    });
   
    
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function createPopupContent(contact) {
   
    const timestamp = contact.timestamp ? new Date(contact.timestamp).toLocaleString() : 'N/A';
    
    
    const description = contact.description ? contact.description.trim() : 'N/A';
    
    return `
        <div class="contact-popup">
            <div class="popup-row"><strong>Type:</strong> ${contact.type || 'N/A'}</div>
            <div class="popup-row"><strong>Speed:</strong> ${contact.speed || 0} knots</div>
            <div class="popup-row"><strong>Significance:</strong> ${contact.significance || 'N/A'}</div>
            <div class="popup-row"><strong>Timestamp:</strong> ${timestamp}</div>
            <div class="popup-row"><strong>Heading:</strong> ${contact.heading ? contact.heading + '°' : 'N/A'}</div>
            <div class="popup-row description">
                <strong>Description:</strong><br>
                ${description}
            </div>
        </div>
    `;
}

function connectWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("WebSocket is already connected");
        return;
    }

    socket = new WebSocket("ws://localhost:8000/ws");

    socket.onmessage = function(event) {
        try {
            let contact = JSON.parse(event.data);
            console.log("Received contact:", contact);

            if (contact.latitude && contact.longitude) {
                // Add new marker
                addMarkerToMap(contact);

                // Update radar chart
                radarChartData.push({
                    type: contact.type,
                    significance_level: getSignificanceLevel(contact.significance)
                });

                if (radarChartData.length > 10) {
                    radarChartData.shift();
                }
                updateRadarChart(radarChartData);
            }
        } catch (error) {
            console.error("Error processing websocket message:", error);
        }
    };

    socket.onclose = function(event) {
        console.log("WebSocket connection closed:", event.code, event.reason);
        
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            console.log(`Attempting to reconnect... (${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
            reconnectAttempts++;
            setTimeout(connectWebSocket, RECONNECT_DELAY);
        } else {
            console.error("Max reconnection attempts reached. Please refresh the page.");
        }
    };

    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
    };

    socket.onopen = function() {
        console.log("WebSocket connected successfully");
        reconnectAttempts = 0;
        
        // Fetch initial contacts
        fetch('http://localhost:8000/initial_contacts')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Initial contacts:", data);
                addMarkersToMap(data);
            })
            .catch(error => {
                console.error("Error fetching initial data:", error);
            });
    };
}

function getSignificanceLevel(significance) {
    switch(significance?.toLowerCase()) {
        case 'routine':
            return 30;
        case 'suspicious':
            return 60;
        case 'threatening':
            return 90;
        default:
            return 50;
    }
}

function updateRadarChart(data) {
    let ctx = document.getElementById('radarChart').getContext('2d');
    let labels = data.map(item => item.type);
    let significanceData = data.map(item => item.significance_level);

    if (window.myRadarChart) {
        window.myRadarChart.destroy();
    }

    window.myRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Significance Level',
                data: significanceData,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                r: {
                    ticks: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            },
            animation: {
                duration: 500
            }
        }
    });
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    updateRadarChart([]);
    connectWebSocket();
});

// Add event listener for page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            reconnectAttempts = 0;
            connectWebSocket();
        }
    }
});