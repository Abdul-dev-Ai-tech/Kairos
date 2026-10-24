/* Location is requested only after the customer presses this button. */
(() => {
  const button=document.querySelector('[data-get-location]');
  if(!button)return;
  const form=button.closest('form'),feedback=form.querySelector('[data-location-feedback]'),clear=form.querySelector('[data-clear-location]');
  button.addEventListener('click',()=>{
    if(!navigator.geolocation){feedback.textContent='Your browser does not support location sharing. Paste a Google Maps pin or enter your complete address.';return;}
    button.disabled=true;feedback.textContent='Waiting for your location permission…';
    navigator.geolocation.getCurrentPosition(position=>{
      form.elements.latitude.value=position.coords.latitude.toFixed(7);form.elements.longitude.value=position.coords.longitude.toFixed(7);
      feedback.textContent='Location pin added. Please check your area and delivery address before ordering.';clear.hidden=false;button.disabled=false;
    },()=>{feedback.textContent='Location was not shared. You can still enter your full address or paste a Google Maps pin.';button.disabled=false;},{enableHighAccuracy:true,timeout:12000,maximumAge:60000});
  });
  clear.addEventListener('click',()=>{form.elements.latitude.value='';form.elements.longitude.value='';feedback.textContent='Location pin removed.';clear.hidden=true;});
})();
