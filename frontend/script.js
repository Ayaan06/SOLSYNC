// Initialize Chart.js
const ctx = document.getElementById('marketChart').getContext('2d');
let marketChart;

// Sample market data
const marketData = {
    labels: [],
    datasets: [
        {
            label: 'BTC/USD',
            data: [],
            borderColor: '#4f46e5',
            borderWidth: 2,
            fill: false,
            tension: 0.1
        },
        {
            label: 'ETH/USD',
            data: [],
            borderColor: '#8b5cf6',
            borderWidth: 2,
            fill: false,
            tension: 0.1
        },
        {
            label: 'SOL/USD',
            data: [],
            borderColor: '#14b8a6',
            borderWidth: 2,
            fill: false,
            tension: 0.1
        }
    ]
};

// Chart configuration
const chartConfig = {
    type: 'line',
    data: marketData,
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            y: {
                beginAtZero: false,
                grid: {
                    color: '#374151'
                },
                ticks: {
                    color: '#9ca3af'
                }
            },
            x: {
                grid: {
                    color: '#374151'
                },
                ticks: {
                    color: '#9ca3af'
                }
            }
        }
    }
};

// Initialize chart
marketChart = new Chart(ctx, chartConfig);

// Timeframe switching
document.querySelectorAll('.timeframe-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        updateChartData(btn.dataset.timeframe);
    });
});

let ws;
const apiKey = 'YOUR_API_KEY'; // Will need to get this from user

function connectWebSocket() {
    ws = new WebSocket('wss://ws.coincap.io/prices?assets=bitcoin,ethereum,solana');
    
    ws.onmessage = (message) => {
        const data = JSON.parse(message.data);
        const timestamp = new Date().toLocaleTimeString();
        
        // Update BTC data
        if (data.bitcoin) {
            marketChart.data.datasets[0].data.push(data.bitcoin);
        }
        
        // Update ETH data
        if (data.ethereum) {
            marketChart.data.datasets[1].data.push(data.ethereum);
        }
        
        // Update SOL data
        if (data.solana) {
            marketChart.data.datasets[2].data.push(data.solana);
        }
        
        // Update labels
        marketChart.data.labels.push(timestamp);
        
        // Keep only last 100 data points
        if (marketChart.data.labels.length > 100) {
            marketChart.data.labels.shift();
            marketChart.data.datasets.forEach(dataset => dataset.data.shift());
        }
        
        marketChart.update();
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket connection closed');
        setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
    };
}

function updateChartData(timeframe) {
    // Disconnect existing WebSocket if any
    if (ws) {
        ws.close();
    }
    
    // Connect new WebSocket with appropriate timeframe
    connectWebSocket();
}

function generateSampleData(timeframe) {
    // Generate sample data based on timeframe
    const baseData = [40000, 42000, 38000, 45000, 47000, 43000, 48000];
    return {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
        data: baseData.map(value => value * (1 + Math.random() * 0.1 - 0.05))
    };
}

// Order form handling
const orderForm = document.getElementById('orderForm');
orderForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const orderType = document.getElementById('orderType').value;
    const orderSide = document.getElementById('orderSide').value;
    const orderAmount = parseFloat(document.getElementById('orderAmount').value);

    if (isNaN(orderAmount) || orderAmount <= 0) {
        alert('Please enter a valid amount');
        return;
    }

    // Here you would send the order to your backend
    console.log('Placing order:', { orderType, orderSide, orderAmount });
    alert('Order placed successfully!');
    orderForm.reset();
});

// Tab navigation for strategies
document.querySelectorAll('.tab-link').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all tabs and content
        document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding content
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});

// Balance formatting
const balanceElement = document.querySelector('.balance');
if (balanceElement) {
    const balance = parseFloat(balanceElement.textContent.replace(/[^0-9.]/g, ''));
    balanceElement.textContent = `$${balance.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

// Deposit/Withdraw buttons
document.querySelector('.btn-deposit')?.addEventListener('click', () => {
    // Implement deposit functionality
    console.log('Deposit clicked');
});

document.querySelector('.btn-withdraw')?.addEventListener('click', () => {
    // Implement withdraw functionality
    console.log('Withdraw clicked');
});
