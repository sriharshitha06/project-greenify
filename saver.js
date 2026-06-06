// Get URL parameters
const urlParams = new URLSearchParams(window.location.search);
const totalCF = parseFloat(urlParams.get('totalCF'));
const inc = parseFloat(urlParams.get('inc'));
const cf = parseFloat(urlParams.get('cf'));
const saver = parseFloat(urlParams.get('saver'));
const resultText = urlParams.get('result');

// Display result
document.getElementById('result').innerText = resultText;
//Your monthly carbon footprint is approximately ${totalCF.toFixed(2)} kg CO2e/month.;


// Create smaller pie chart
const ctx = document.getElementById('pie-chart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'pie',
  data: {
    labels: ['Carbon Footprint', 'Saver'],
    datasets: [{
      label: [],
      data: [cf, saver],
      backgroundColor: ["#fd0312", "#2dfd03"],
      borderColor: ['#2dfd03'],
      borderWidth: 1
    }]
  },
  options: {
    maintainAspectRatio: false,
    responsive: false,
    legend: {
      display: true,
      position: 'bottom'
    },
    layout: {
      padding: {
        top: 20,
        right: 20,
        bottom: 20,
        left: 20
      }
    },
    width: 400,
    height: 400
  }
});
