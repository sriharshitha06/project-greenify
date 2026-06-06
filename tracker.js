document.getElementById('calculate').addEventListener('click', function(event) {
  event.preventDefault();
  
  const electricityInput = document.getElementById('electricity');
  const lpgInput = document.getElementById('lpg');
  const petrolInput = document.getElementById('petrol');
  const dieselInput = document.getElementById('diesel');
  const cylInput = document.getElementById('cyl');
  const cngInput = document.getElementById('cng');
  const electricity = parseFloat(electricityInput.value);
  const lpg = parseFloat(lpgInput.value);
  const petrol = parseFloat(petrolInput.value);
  const diesel = parseFloat(dieselInput.value);
  const cyl = parseFloat(cylInput.value);
  const cng = parseFloat(cngInput.value);
  
  if (isNaN(electricity) || isNaN(lpg) || isNaN(petrol) || isNaN(diesel)) {
    alert('Please enter valid numbers');
    return;
  }
  
  const electricityCF = electricity * 0.62; // kg CO2e/month
  const lpgCF = lpg * 24.4/cyl; // kg CO2e/month
  const petrolCF = petrol * 2.35; // kg CO2e/month
  const dieselCF = diesel * 2.64; // kg CO2e/month
  const cngCF = cng*0.054* 53.6 * 0.43 ; 
  const totalCF = electricityCF + lpgCF + petrolCF + dieselCF + cngCF; // kg CO2e/month
 // const tonnesCF = totalCF / 1000; // tonnes CO2e/month
  let cf, inc , saver;
  if (totalCF < 122.7) {
  cf = 0;
  inc=0;
  saver = 100;
  resultText=`Your monthly carbon footprint is approximately ${totalCF.toFixed(2)} kg CO2e/month. 
  Congratulations it is below the average per capita Carbon Footprint. Keep going!!`
} else {
  inc = totalCF - 122.7;
  _cf = ((inc / 122.7) * 100);
  cf = _cf / 5.09;
  saver = 100 - cf;
  
  resultText= `Your monthly carbon footprint is approximately ${totalCF.toFixed(2)} kg CO2e/month.
   You emit approximately ${inc.toFixed(2)}kg CO2e more than the average per capita Carbon footprint!!! 
   Consider reducing your energy consumption.`;
}
 // document.getElementById('result').innerText = `Your monthly carbon footprint is approximately ${totalCF.toFixed(2)} kg CO2e/month.
  // You emit approximately ${inc.toFixed(2)}kg CO2e more than the average per capita Carbon footprint!!! `;
  
  // Create pie chart
 // const ctx = document.getElementById('pie-chart').getContext('2d');
 // const chart = new Chart(ctx, {
   // type: 'pie',
   // data: {
     // labels: ['Carbon Footprint','Saver'],
      // datasets: [{
        //label: [],
        //data: [cf,saver],
        // backgroundColor: ["#fd0312", "#2dfd03"], // Red color
       // borderColor: ['rgba(255, 0, 0, 1)'],
       // borderWidth: 1
     // }]
   // },
    // options: {
     // legend: {
       // display: true,
        // position: 'bottom'
      // }
     // }
   //});
// });

// Redirect to result page with calculated values
const url = `saver.html?totalCF=${totalCF}&inc=${inc}&cf=${cf}&saver=${saver}&result=${resultText}`;
window.location.href = url;
});
