document.addEventListener('DOMContentLoaded', function() {
    // Set current date
    const today = new Date();
    document.getElementById('current-date').textContent = today.toLocaleDateString('en-US', { 
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Sample data - in a real app, you'd fetch this from a server
    const userData = {
        name: "EcoChampion",
        avatar: "EC",
        todayCO2: 5.2, // kg saved today
        totalCO2: 42.7, // kg saved total
        weeklyProgress: [3.1, 4.5, 2.8, 5.2, 6.0, 4.3, 5.2], // Last 7 days
        leaderboard: [
            { id: 1, name: "GreenGuru", dailyCO2: 8.1, totalCO2: 65.3, avatar: "GG" },
            { id: 2, name: "EcoMaster", dailyCO2: 7.5, totalCO2: 58.2, avatar: "EM" },
            { id: 3, name: "You", dailyCO2: 5.2, totalCO2: 42.7, avatar: "EC", isYou: true },
            { id: 4, name: "PlanetPal", dailyCO2: 4.8, totalCO2: 38.9, avatar: "PP" },
            { id: 5, name: "NatureNinja", dailyCO2: 4.3, totalCO2: 35.1, avatar: "NN" }
        ]
    };

    // Calculate points (1000 - (CO₂ * 10))
    function calculatePoints(co2) {
        const points = 1000 - (co2 * 10);
        return Math.max(0, Math.round(points)); // Never go below 0
    }

    // Update user points
    const todayPoints = calculatePoints(userData.todayCO2);
    const totalPoints = calculatePoints(userData.totalCO2);
    
    document.getElementById('today-points').textContent = todayPoints;
    document.getElementById('today-co2').textContent = `${userData.todayCO2.toFixed(1)}kg CO₂ saved`;
    document.getElementById('total-points').textContent = totalPoints;

    // Initialize chart
    const ctx = document.getElementById('progressChart').getContext('2d');
    const progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['6d ago', '5d ago', '4d ago', '3d ago', '2d ago', 'Yesterday', 'Today'],
            datasets: [{
                label: 'CO₂ Saved (kg)',
                data: userData.weeklyProgress,
                backgroundColor: 'rgba(76, 175, 80, 0.2)',
                borderColor: 'rgba(76, 175, 80, 1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Kilograms Saved'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y}kg (${calculatePoints(context.parsed.y)} pts)`;
                        }
                    }
                }
            }
        }
    });

    // Leaderboard functionality
    let currentPeriod = 'daily';
    const leaderboardBody = document.getElementById('leaderboard-body');
    const periodButtons = document.querySelectorAll('.time-btn');

    function renderLeaderboard(period) {
        // Sort based on selected period
        const sortedData = [...userData.leaderboard].sort((a, b) => {
            return b[`${period}CO2`] - a[`${period}CO2`]; // Higher CO2 saved = better
        });

        leaderboardBody.innerHTML = sortedData.map((entry, index) => `
            <div class="leaderboard-entry ${entry.isYou ? 'you' : ''}">
                <span class="rank">${index + 1}</span>
                <span class="user">
                    <span class="user-avatar">${entry.avatar}</span>
                    ${entry.name}
                </span>
                <span class="co2">${entry[`${period}CO2`].toFixed(1)}kg</span>
                <span class="points">${calculatePoints(entry[`${period}CO2`])}</span>
            </div>
        `).join('');
    }

    // Initial render
    renderLeaderboard(currentPeriod);

    // Period switcher
    periodButtons.forEach(button => {
        button.addEventListener('click', function() {
            periodButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            currentPeriod = this.dataset.period;
            renderLeaderboard(currentPeriod);
        });
    });

    // In a real app, you would:
    // 1. Fetch user data from your backend API
    // 2. Update the chart and leaderboard in real-time
    // 3. Calculate points on the server side
    // 4. Implement authentication for "your" stats
});