import csv, math, os, re, statistics, subprocess, threading, time
from collections import defaultdict, deque
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP='KukSense'; VERSION='0.1.0'
BSSID_RE=re.compile(r'^\s*BSSID\s+\d+\s*:\s*([0-9A-Fa-f:]{17})')
SSID_RE=re.compile(r'^\s*SSID\s+\d+\s*:\s*(.*)$')
SIGNAL_RE=re.compile(r'^\s*Signal\s*:\s*(\d+)%')

class Engine:
    def __init__(self, window=20):
        self.window=window; self.history=defaultdict(lambda: deque(maxlen=window)); self.baseline={}; self.threshold=4.0
    def scan(self):
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        p=subprocess.run(['netsh','wlan','show','networks','mode=bssid'],capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=flags)
        if p.returncode: raise RuntimeError(p.stderr.strip() or 'Wi-Fi scan failed')
        out=[]; ssid=''; bssid=None
        for line in p.stdout.splitlines():
            m=SSID_RE.match(line)
            if m: ssid=m.group(1).strip(); continue
            m=BSSID_RE.match(line)
            if m: bssid=m.group(1).lower(); continue
            m=SIGNAL_RE.match(line)
            if m and bssid:
                signal=int(m.group(1)); out.append((ssid,bssid,signal)); bssid=None
        return out
    def process(self, samples):
        rows=[]
        for ssid,bssid,signal in samples:
            q=self.history[bssid]; q.append(signal)
            sd=statistics.stdev(q) if len(q)>1 else 0.0
            base=self.baseline.get(bssid,0.0); effective=max(self.threshold,base*2.2)
            score=min(100.0,(sd/effective)*100) if effective else 0
            state='calibrating' if len(q)<8 else ('high-activity' if sd>=effective*1.8 else 'possible-movement' if sd>=effective else 'quiet')
            rows.append({'time':datetime.now(timezone.utc).isoformat(),'ssid':ssid,'bssid':bssid,'signal':signal,'dbm':round(signal/2-100,1),'stddev':round(sd,2),'score':round(score,1),'state':state})
        return rows
    def calibrate(self):
        self.baseline={k:(statistics.stdev(v) if len(v)>1 else 0.0) for k,v in self.history.items()}

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f'{APP} {VERSION}'); self.geometry('1080x700'); self.minsize(900,600)
        self.engine=Engine(); self.running=False; self.rows=[]; self.csv_path=os.path.join(os.path.expanduser('~'),'Documents','KukSense','sessions',f"session-{datetime.now():%Y%m%d-%H%M%S}.csv")
        self._style(); self._ui(); self.protocol('WM_DELETE_WINDOW',self.close)
    def _style(self):
        s=ttk.Style(self); s.theme_use('vista'); s.configure('Title.TLabel',font=('Segoe UI Semibold',22)); s.configure('Metric.TLabel',font=('Segoe UI Semibold',18)); s.configure('State.TLabel',font=('Segoe UI Semibold',15))
    def _ui(self):
        top=ttk.Frame(self,padding=18); top.pack(fill='x'); ttk.Label(top,text='KukSense',style='Title.TLabel').pack(side='left'); ttk.Label(top,text='Camera-free Wi-Fi activity experiment').pack(side='left',padx=15)
        self.btn=ttk.Button(top,text='Start sensing',command=self.toggle); self.btn.pack(side='right'); ttk.Button(top,text='Calibrate room',command=self.calibrate).pack(side='right',padx=8); ttk.Button(top,text='Export CSV',command=self.export).pack(side='right')
        metrics=ttk.Frame(self,padding=(18,4)); metrics.pack(fill='x')
        self.state=tk.StringVar(value='Stopped'); self.score=tk.StringVar(value='0'); self.networks=tk.StringVar(value='0'); self.samples=tk.StringVar(value='0')
        for title,var in [('STATE',self.state),('ACTIVITY SCORE',self.score),('NETWORKS',self.networks),('SAMPLES',self.samples)]:
            f=ttk.LabelFrame(metrics,text=title,padding=14); f.pack(side='left',fill='x',expand=True,padx=5); ttk.Label(f,textvariable=var,style='Metric.TLabel').pack()
        body=ttk.Panedwindow(self,orient='horizontal'); body.pack(fill='both',expand=True,padx=18,pady=14)
        left=ttk.LabelFrame(body,text='Live activity',padding=10); right=ttk.LabelFrame(body,text='Nearby Wi-Fi signals',padding=10); body.add(left,weight=3); body.add(right,weight=2)
        self.canvas=tk.Canvas(left,bg='#101318',highlightthickness=0); self.canvas.pack(fill='both',expand=True); self.canvas.bind('<Configure>',lambda e:self.draw())
        self.tree=ttk.Treeview(right,columns=('ssid','signal','std','state'),show='headings',height=18)
        for c,t,w in [('ssid','SSID',150),('signal','Signal',60),('std','Variance',70),('state','State',110)]: self.tree.heading(c,text=t); self.tree.column(c,width=w,anchor='center')
        self.tree.pack(fill='both',expand=True)
        bottom=ttk.Frame(self,padding=(18,0,18,14)); bottom.pack(fill='x'); self.status=tk.StringVar(value='Ready. Keep laptop and router fixed for meaningful comparison.'); ttk.Label(bottom,textvariable=self.status).pack(side='left')
    def toggle(self):
        self.running=not self.running; self.btn.config(text='Stop sensing' if self.running else 'Start sensing'); self.state.set('Starting…' if self.running else 'Stopped')
        if self.running: threading.Thread(target=self.loop,daemon=True).start()
    def loop(self):
        while self.running:
            try:
                rows=self.engine.process(self.engine.scan()); self.after(0,self.update_ui,rows); self.save(rows)
            except Exception as e: self.after(0,self.status.set,f'Error: {e}')
            time.sleep(2)
    def update_ui(self,rows):
        if not rows:return
        self.rows.extend(rows); self.rows=self.rows[-240:]; top=max(rows,key=lambda r:r['score']); self.state.set(top['state'].replace('-',' ').title()); self.score.set(f"{top['score']:.0f}/100"); self.networks.set(str(len({r['bssid'] for r in rows}))); self.samples.set(str(len(self.rows)))
        for x in self.tree.get_children(): self.tree.delete(x)
        for r in sorted(rows,key=lambda x:x['signal'],reverse=True)[:20]: self.tree.insert('', 'end', values=(r['ssid'] or '(hidden)',f"{r['signal']}%",r['stddev'],r['state']))
        self.status.set(f"Sensing • {datetime.now():%H:%M:%S} • Data saved locally"); self.draw()
    def draw(self):
        c=self.canvas; c.delete('all'); w=max(c.winfo_width(),10); h=max(c.winfo_height(),10); vals=[r['score'] for r in self.rows[-120:]]
        c.create_text(18,18,text='RF activity score • last readings',fill='#d7dde8',anchor='nw',font=('Segoe UI Semibold',12))
        if len(vals)<2:return
        pts=[]
        for i,v in enumerate(vals): pts.extend((i*(w-30)/(len(vals)-1)+15,h-25-(v/100)*(h-65)))
        c.create_line(*pts,fill='#4f8cff',width=3,smooth=True); c.create_line(15,h-25,w-15,h-25,fill='#343a46')
    def calibrate(self):
        if not self.engine.history: messagebox.showinfo(APP,'Start sensing and collect at least 30–60 seconds of quiet-room data first.'); return
        self.engine.calibrate(); self.status.set(f'Room calibrated from {len(self.engine.baseline)} Wi-Fi signals.')
    def save(self,rows):
        if not rows:return
        os.makedirs(os.path.dirname(self.csv_path),exist_ok=True); exists=os.path.exists(self.csv_path)
        with open(self.csv_path,'a',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());
            if not exists:w.writeheader()
            w.writerows(rows)
    def export(self):
        if not os.path.exists(self.csv_path): messagebox.showinfo(APP,'No session data yet.'); return
        dst=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='kuksense-session.csv',filetypes=[('CSV','*.csv')])
        if dst:
            import shutil; shutil.copy2(self.csv_path,dst); self.status.set(f'Exported to {dst}')
    def close(self): self.running=False; self.destroy()

if __name__=='__main__': App().mainloop()
