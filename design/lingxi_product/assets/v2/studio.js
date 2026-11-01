
const $=id=>document.getElementById(id);let online=false,busy=false;
function note(message){$('receipt').textContent=message}
async function api(path,payload){const options={cache:'no-store'};if(payload!==undefined){options.method='POST';options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(payload)}const response=await fetch(path,options);let data={};try{data=await response.json()}catch{throw Error('工作台没有返回有效状态')}if(!response.ok)throw Error(data.error||data.message||`请求被拒绝 (${response.status})`);return data}
function setControls(){document.querySelectorAll('[data-theater],[data-motion],#motion-enabled').forEach(el=>{el.disabled=!online||busy});document.querySelectorAll('[data-eye]').forEach(el=>{el.disabled=!online||busy})}
async function run(fn){if(busy)return;busy=true;setControls();try{await fn()}catch(error){note(error.message)}finally{busy=false;setControls();await updateStatus()}}
async function updateStatus(){try{const status=await api('/api/status');online=status.boardOnline!==false;$('connection').textContent=online?'工作台已连接':'工作台未连接';$('status-dot').classList.toggle('online',online);$('motion-enabled').checked=!!status.motionEnabled;if(status.theater?.state==='running')note('表演进行中，可随时停止')}catch{online=false;$('connection').textContent='工作台未连接';$('status-dot').classList.remove('online')}setControls()}
document.querySelectorAll('[data-theater]').forEach(button=>button.onclick=()=>run(async()=>{const result=await api('/api/theater',{action:button.dataset.theater});note(result.message||'表演已接受')}));
document.querySelectorAll('[data-eye]').forEach(button=>button.onclick=()=>run(async()=>{await api('/api/eyes',{mode:Number(button.dataset.eye),durationMs:5000,contrast:127});note('表情指令已发送')}));
document.querySelectorAll('[data-motion]').forEach(button=>button.onclick=()=>run(async()=>{const result=await api('/api/motion',{action:button.dataset.motion});note(result.message||'动作指令已发送')}));
$('motion-enabled').onchange=()=>run(async()=>{const enabled=$('motion-enabled').checked;const result=await api('/api/motion-enable',{enabled});note(result.enabled?'运动已启用':'运动已禁用，已发送停止')});
$('stop').onclick=()=>run(async()=>{const result=await api('/api/stop',{});note(result.message||'已发送停止，未执行的动作已取消')});

const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){entry.target.classList.add('visible');observer.unobserve(entry.target)}}},{threshold:.08});
document.querySelectorAll('[data-reveal]').forEach(el=>observer.observe(el));
updateStatus();setInterval(updateStatus,5000);
