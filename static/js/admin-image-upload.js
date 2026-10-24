/* Avoid Vercel's request limit before a multi-image admin upload is submitted. */
document.addEventListener('submit', event => {
  const form=event.target;
  const files=[...form.querySelectorAll('input[type=file]')].flatMap(input=>[...input.files]);
  if(files.reduce((sum,file)=>sum+file.size,0)>3800000){
    event.preventDefault();
    let warning=form.querySelector('[data-upload-limit]');
    if(!warning){warning=document.createElement('p');warning.dataset.uploadLimit='';warning.className='errornote';warning.setAttribute('role','alert');form.prepend(warning);}
    warning.textContent='Save less than 3.8 MB of pictures at a time. On Vercel use images below 1 MB each, save, then add more pictures.';
    warning.scrollIntoView({block:'center'});
  }
},true);
