from pathlib import Path
import time,subprocess,json
samples=[]
for i in range(300):
 m={a.split(':')[0]:int(a.split()[1]) for a in Path('/proc/meminfo').read_text().splitlines() if a.startswith(('MemAvailable:','SwapFree:'))}
 samples.append(m)
 if m['MemAvailable']<1536*1024:
  subprocess.run(['systemctl','stop','--no-block','native-steam-poc.service']);break
 time.sleep(1)
else:subprocess.run(['systemctl','stop','--no-block','native-steam-poc.service'])
Path('/tmp/native-steam-poc/memory.json').write_text(json.dumps(samples))
