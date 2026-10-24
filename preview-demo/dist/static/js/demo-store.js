/* Browser-local demo storage. This is not a public database or an authentication boundary. */
(() => {
  'use strict';
  const KEY='kairos-manager-demo-v2';
  const clone=value=>JSON.parse(JSON.stringify(value));
  const defaults=()=>({version:2,products:clone(window.KAIROS_DEMO),categories:[
    {id:'men',name:'Men’s Watches',description:'Character in every detail.',image:'/media/images/8e40aa3c22704238986a81cf76bc022a.webp'},
    {id:'women',name:'Women’s Watches',description:'An expression, entirely yours.',image:'/media/images/8cb9fc713f154fbcab3b80d65194fed3.webp'},
    {id:'unisex',name:'Unisex Watches',description:'Good design belongs to everyone.',image:'/media/images/855ff105a86341038eb989557d58f3be.webp'}
  ],settings:{announcement:'EVERY SECOND, YOUR STYLE. · DISCOVER THE KAIROS COLLECTION',tagline:'Every Second, Your Style.',heroEyebrow:'THE KAIROS SIGNATURE',heroLine1:'Time, made',heroLine2:'personal.',heroDescription:'Considered details. Quiet confidence.\nFind a timepiece that moves with you.',whatsapp:'923157292819',instagram:'https://www.instagram.com/2.kairos.store/',email:'',logo:''},orders:[]});
  let state;
  try{const saved=JSON.parse(localStorage.getItem(KEY));state=saved?.version===2&&Array.isArray(saved.products)&&Array.isArray(saved.categories)?saved:defaults();}catch{state=defaults();}
  // Apply the business contact details to older browser demos once.
  if(state.contactVersion!==1){state.settings.whatsapp='923157292819';state.settings.instagram='https://www.instagram.com/2.kairos.store/';state.contactVersion=1;try{localStorage.setItem(KEY,JSON.stringify(state));}catch{}}
  const listeners=new Set();
  function commit(next){localStorage.setItem(KEY,JSON.stringify(next));state=next;listeners.forEach(fn=>fn());window.dispatchEvent(new CustomEvent('kairos:changed'));}
  function mutate(fn){const next=clone(state);fn(next);commit(next);}
  const slug=value=>String(value).toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,70);
  function validateProduct(p){
    if(!p.name?.trim()||p.name.length>120)throw Error('Enter a product name (1–120 characters).');
    if(!p.sku?.trim())throw Error('Add a product SKU.');
    if(state.products.some(x=>x.id!==p.id&&x.sku.toLowerCase()===p.sku.toLowerCase()))throw Error('This SKU already belongs to another product.');
    if(!state.categories.some(c=>c.id===p.collection))throw Error('Select a category.');
    if(!Number.isFinite(Number(p.regularPrice))||Number(p.regularPrice)<=0||Number(p.regularPrice)>99999999)throw Error('Enter a valid regular price.');
    if(!Number.isFinite(Number(p.price))||Number(p.price)<=0||Number(p.price)>Number(p.regularPrice))throw Error('Sale price must be positive and at most the regular price.');
    if(!p.variants?.length)throw Error('Keep at least one product variant.');
    if(p.variants.some(v=>!v.name.trim()||!v.sku.trim()||!Number.isInteger(v.stock)||v.stock<0||v.stock>999999||!Number.isFinite(Number(v.price))||Number(v.price)<=0))throw Error('Check each variant’s name, SKU, price and stock.');
    if(new Set(p.variants.map(v=>v.sku.toLowerCase())).size!==p.variants.length)throw Error('Variant SKUs must be different.');
    if(p.variants.some(v=>state.products.some(x=>x.id!==p.id&&x.variants.some(a=>a.sku.toLowerCase()===v.sku.toLowerCase()))))throw Error('A variant SKU is already in use.');
  }
  window.KairosStore={
    get state(){return state;}, get products(){return state.products.filter(p=>p.status==='published');},
    clone,slug,subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);},
    saveProduct(p){validateProduct(p);p.name=p.name.trim();p.sku=p.sku.trim();p.collectionName=state.categories.find(c=>c.id===p.collection).name;p.category=p.collection;p.stock=p.variants.reduce((a,v)=>a+v.stock,0);p.sale=Number(p.price)<Number(p.regularPrice);p.cover=p.images[0]||null;mutate(s=>{const i=s.products.findIndex(x=>x.id===p.id);if(i<0)s.products.unshift(p);else s.products[i]=p;});},
    deleteProduct(id){mutate(s=>{s.products=s.products.filter(p=>p.id!==id);});},
    saveCategory(c){if(!c.name.trim()||c.name.length>80)throw Error('Enter a category name (1–80 characters).');if(state.categories.some(x=>x.id!==c.id&&x.name.toLowerCase()===c.name.toLowerCase()))throw Error('This category already exists.');mutate(s=>{const i=s.categories.findIndex(x=>x.id===c.id);if(i<0)s.categories.push(c);else s.categories[i]=c;s.products.forEach(p=>{if(p.collection===c.id)p.collectionName=c.name;});});},
    deleteCategory(id,reassign){if(state.categories.length<2)throw Error('Keep at least one category.');if(state.products.some(p=>p.collection===id)&&!state.categories.some(c=>c.id===reassign&&c.id!==id))throw Error('Choose a category for the existing products.');mutate(s=>{s.categories=s.categories.filter(c=>c.id!==id);s.products.forEach(p=>{if(p.collection===id){p.collection=reassign;p.category=reassign;p.collectionName=s.categories.find(c=>c.id===reassign).name;}});});},
    saveSettings(settings){const w=settings.whatsapp.replace(/[\s+()-]/g,'');if(w&&!/^\d{8,15}$/.test(w))throw Error('Use an international WhatsApp number, e.g. 923001234567.');let instagram=settings.instagram.trim();if(instagram&&!instagram.startsWith('https://'))instagram='https://www.instagram.com/'+instagram.replace(/^@/,'').replace(/\/$/,'')+'/';if(instagram){let url;try{url=new URL(instagram);}catch{throw Error('Check the Instagram handle or URL.');}if(!['instagram.com','www.instagram.com'].includes(url.hostname)||url.protocol!=='https:')throw Error('Use an instagram.com profile URL.');}mutate(s=>{s.settings={...settings,whatsapp:w,instagram};});},
    addOrder(order){mutate(s=>s.orders.unshift(order));},
    updateOrder(id,status){if(!['Pending','Confirmed','Processing','Shipped','Delivered','Cancelled'].includes(status))throw Error('Choose a valid order status.');mutate(s=>{const o=s.orders.find(o=>o.number===id);if(o)o.status=status;});},
    reset(){commit(defaults());},
    async image(file){
      if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('Choose a JPG, PNG or WebP image.');
      if(file.size>8*1024*1024)throw Error('Images must be smaller than 8 MB.');
      const image=await createImageBitmap(file);
      try{if(image.width*image.height>24000000||image.width<20||image.height<20)throw Error('Choose an image between 20 pixels and 24 megapixels.');const ratio=Math.min(1,1200/Math.max(image.width,image.height));const canvas=document.createElement('canvas');canvas.width=Math.round(image.width*ratio);canvas.height=Math.round(image.height*ratio);canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);const result=canvas.toDataURL('image/webp',.8);if(result.length>700000)throw Error('Please choose a simpler or smaller image.');return {thumb:result,medium:result,url:result,alt:file.name.replace(/\.[^.]+$/,'').slice(0,100)};}finally{image.close();}
    }
  };
})();
