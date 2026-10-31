from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
import sqlite3, csv, io, json, hashlib, hmac, time, os, secrets, datetime, base64

DB = Path(__file__).resolve().parents[1] / 'data' / 'nipunsetu.db'
DB.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='NIPUNSetu API', version='3.5.0', description='FLN decision-support and policy feedback platform')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
SECRET = os.getenv('NIPUNSETU_SECRET', 'change-this-demo-secret-before-deployment')


def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def pw_hash(p): return hashlib.pbkdf2_hmac('sha256', p.encode(), b'nipunsetu-v1', 120000).hex()
def b64u(raw): return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()
def jwt_sign(claims):
    head=b64u(json.dumps({'alg':'HS256','typ':'JWT'},separators=(',',':')).encode()); body=b64u(json.dumps(claims,separators=(',',':')).encode()); msg=f'{head}.{body}'; sig=b64u(hmac.new(SECRET.encode(),msg.encode(),hashlib.sha256).digest()); return msg+'.'+sig
def jwt_verify(token):
    head,body,sig=token.split('.'); msg=f'{head}.{body}'; expected=b64u(hmac.new(SECRET.encode(),msg.encode(),hashlib.sha256).digest())
    if not hmac.compare_digest(sig,expected): raise ValueError('signature')
    claims=json.loads(base64.urlsafe_b64decode(body+'='*((4-len(body)%4)%4)))
    if claims.get('iss')!='nipunsetu' or claims.get('aud')!='nipunsetu-web' or claims.get('exp',0)<time.time(): raise ValueError('claims')
    return claims
def token_for(user):
    now=int(time.time()); return jwt_sign({'sub':user['id'],'role':user['role'],'iat':now,'exp':now+28800,'iss':'nipunsetu','aud':'nipunsetu-web'})

def current_user(authorization: Optional[str]=Header(None)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Sign in required')
    try:
        claims=jwt_verify(authorization[7:])
        c=conn(); u=c.execute('SELECT id,name,email,role,school_id,district FROM users WHERE id=?',(claims['sub'],)).fetchone(); c.close()
        if not u or u['role'] != claims.get('role'): raise ValueError()
        return dict(u)
    except Exception: raise HTTPException(401,'Invalid or expired access token')

def log(c, user, action, entity, entity_id, details=''):
    c.execute('INSERT INTO audit_logs(user_id,action,entity,entity_id,details,created_at) VALUES(?,?,?,?,?,datetime("now"))',(user['id'] if user else None,action,entity,str(entity_id),details))

def init_db():
 c=conn(); c.executescript('''
 CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,school_id TEXT,district TEXT);
 CREATE TABLE IF NOT EXISTS schools(id TEXT PRIMARY KEY,name TEXT,block TEXT,district TEXT,state TEXT);
 CREATE TABLE IF NOT EXISTS learners(id TEXT PRIMARY KEY,name TEXT,grade INTEGER,school_id TEXT,gender TEXT,attendance REAL,reading_level TEXT,numeracy_level TEXT,reading_score REAL,numeracy_score REAL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS assessments(id INTEGER PRIMARY KEY AUTOINCREMENT,learner_id TEXT,domain TEXT,score REAL,level TEXT,source TEXT,assessed_on TEXT,assessor TEXT);
 CREATE TABLE IF NOT EXISTS interventions(id INTEGER PRIMARY KEY AUTOINCREMENT,learner_id TEXT,domain TEXT,gap TEXT,recommendation TEXT,status TEXT DEFAULT 'Planned',due_date TEXT,teacher_id TEXT,notes TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,completed_at TEXT);
 CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,action TEXT,entity TEXT,entity_id TEXT,details TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY AUTOINCREMENT,filename TEXT,rows_added INTEGER,source TEXT,imported_by TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS sync_events(id TEXT PRIMARY KEY, user_id TEXT, event_type TEXT, payload TEXT, synced_at TEXT DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS reassessments(id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT, domain TEXT, score REAL, assessed_on TEXT, intervention_id INTEGER, assessor TEXT, notes TEXT);
 ''')
 # Idempotent metadata migration for verified directory records and synthetic demo records.
 cols={r[1] for r in c.execute('PRAGMA table_info(schools)').fetchall()}
 for name,decl in [('udise_code','TEXT'),('data_origin',"TEXT DEFAULT 'Synthetic demo'"),('management','TEXT'),('source_url','TEXT')]:
  if name not in cols: c.execute(f'ALTER TABLE schools ADD COLUMN {name} {decl}')
 if c.execute('SELECT COUNT(*) FROM schools').fetchone()[0]==0:
  schools=[('SCH001','Government Primary School, Sector 12','Noida Urban','Gautam Buddha Nagar','Uttar Pradesh'),('SCH002','Composite School, Dadri','Dadri','Gautam Buddha Nagar','Uttar Pradesh'),('SCH003','Prathmik Vidyalaya, Bisrakh','Bisrakh','Gautam Buddha Nagar','Uttar Pradesh'),('SCH004','Govt Primary School, Jewar','Jewar','Gautam Buddha Nagar','Uttar Pradesh')]
  c.executemany('INSERT INTO schools(id,name,block,district,state) VALUES(?,?,?,?,?)',schools)
  users=[('U1','Aarav Sharma','teacher@demo.in',pw_hash('teacher123'),'teacher','SCH001','Gautam Buddha Nagar'),('U2','Meera Verma','block@demo.in',pw_hash('block123'),'block_officer',None,'Gautam Buddha Nagar'),('U3','Rohan Singh','state@demo.in',pw_hash('state123'),'state_admin',None,'Uttar Pradesh'),('U4','System Admin','admin@demo.in',pw_hash('admin123'),'admin',None,'Uttar Pradesh')]
  c.executemany('INSERT INTO users VALUES(?,?,?,?,?,?,?)',users)
  names=['Aanya','Vivaan','Ishita','Arjun','Saanvi','Kabir','Diya','Reyansh','Anaya','Atharv','Myra','Advait','Kiara','Aarav','Sara','Krish','Navya','Rudra','Tara','Dev']
  import random
  random.seed(42)
  for i in range(80):
   sid=schools[i%4][0]; grade=1+(i%5); r=random.randint(20,100); n=random.randint(15,100); att=random.randint(55,100)
   rl='Independent' if r>=75 else ('Letter' if r>=50 else 'Beginner')
   nl='Grade-ready' if n>=75 else ('Developing' if n>=45 else 'Needs support')
   lid=f'L{i+1:04d}'; c.execute('INSERT INTO learners(id,name,grade,school_id,gender,attendance,reading_level,numeracy_level,reading_score,numeracy_score) VALUES(?,?,?,?,?,?,?,?,?,?)',(lid,names[i%len(names)]+f' {i//20+1}',grade,sid,'F' if i%2 else 'M',att,rl,nl,r,n))
   c.execute('INSERT INTO assessments(learner_id,domain,score,level,source,assessed_on,assessor) VALUES(?,?,?,?,?,?,?)',(lid,'reading',r,rl,'School FLN baseline','2026-09-15','teacher@demo.in'))
   c.execute('INSERT INTO assessments(learner_id,domain,score,level,source,assessed_on,assessor) VALUES(?,?,?,?,?,?,?)',(lid,'numeracy',n,nl,'School FLN baseline','2026-09-15','teacher@demo.in'))
 c.commit(); c.close()
init_db()

# Expand the deterministic demonstration geography and learning panel. All records are synthetic.
def expand_demo_panel():
 import random
 rng=random.Random(20261031)
 # Real school names + UDISE identifiers are drawn from a public school directory
 # referencing UDISE+ records. Learner metrics attached to these schools remain synthetic.
 verified=[
  ('SCH001','P S Myana','Jewar','09100403001'),
  ('SCH002','P S Nagla Shrigopal','Jewar','09100401701'),
  ('SCH003','P S Bhunna Taga','Jewar','09100402501'),
  ('SCH004','Composite School Raunija','Jewar','09100401207'),
  ('SCH005','P S Jhuppa Kalan','Jewar','09100405303'),
  ('SCH006','P S Choti Kanigarhi','Jewar','09100405004'),
 ]
 source='https://in.knowyourschools.com/directory/uttar-pradesh/gautam-buddha-nagar'
 c=conn()
 # Normalise the demo geography to the four blocks shown in the district school directory.
 blocks=['Visrakh','Dadri','Dankaur','Jewar']
 for idx,(sid,name,block,udise) in enumerate(verified):
  c.execute('UPDATE schools SET name=?,block=?,district=?,state=?,udise_code=?,data_origin=?,management=?,source_url=? WHERE id=?',
   (name,block,'Gautam Buddha Nagar','Uttar Pradesh',udise,'Public directory record; learner data synthetic','Government',source,sid))
 for i in range(7,31):
  sid=f'SCH{i:03d}'; block=blocks[(i-1)%4]
  c.execute('INSERT OR IGNORE INTO schools(id,name,block,district,state,udise_code,data_origin,management,source_url) VALUES(?,?,?,?,?,?,?,?,?)',
   (sid,f'Demo Government School {i:02d}',block,'Gautam Buddha Nagar','Uttar Pradesh',None,'Synthetic demonstration school','Demo record',None))
  c.execute('UPDATE schools SET block=?,data_origin=COALESCE(data_origin,?),management=COALESCE(management,?) WHERE id=?',
   (block,'Synthetic demonstration school','Demo record',sid))
 # Existing first four schools and generated learner data stay linked; top up SCH006 and all schools to 12.
 names=['Aarohi','Vihaan','Anvi','Ishaan','Myra','Advik','Saanvi','Reyansh','Kiara','Kabir','Diya','Arnav','Navya','Rudra','Aanya','Yuvaan','Pari','Krish','Tara','Dev']
 for si in range(1,31):
  sid=f'SCH{si:03d}'
  for j in range(12):
   lid=f'DEMO-{si:03d}-{j+1:02d}'
   if c.execute('SELECT 1 FROM learners WHERE id=?',(lid,)).fetchone(): continue
   grade=1+(j%5); reading=rng.randint(24,91); numeracy=rng.randint(20,94); attendance=rng.randint(58,99)
   rl='Independent' if reading>=75 else ('Letter' if reading>=50 else 'Beginner')
   nl='Grade-ready' if numeracy>=75 else ('Developing' if numeracy>=45 else 'Needs support')
   c.execute('INSERT INTO learners(id,name,grade,school_id,gender,attendance,reading_level,numeracy_level,reading_score,numeracy_score) VALUES(?,?,?,?,?,?,?,?,?,?)',(lid,f'{names[(si+j)%len(names)]} {si:02d}{j+1:02d}',grade,sid,'F' if j%2 else 'M',attendance,rl,nl,reading,numeracy))
   for domain,score,level in [('reading',reading,rl),('numeracy',numeracy,nl)]:
    base=max(5,min(100,score-rng.randint(3,18)))
    c.execute('INSERT INTO assessments(learner_id,domain,score,level,source,assessed_on,assessor) VALUES(?,?,?,?,?,?,?)',(lid,domain,base,'Baseline','Synthetic baseline · demo','2026-07-15','DEMO'))
    c.execute('INSERT INTO assessments(learner_id,domain,score,level,source,assessed_on,assessor) VALUES(?,?,?,?,?,?,?)',(lid,domain,score,level,'Synthetic term assessment · demo','2026-10-15','DEMO'))
   if reading<55 or numeracy<50:
    domain='reading' if reading<=numeracy else 'numeracy'
    c.execute('INSERT INTO interventions(learner_id,domain,gap,recommendation,status,due_date,teacher_id,notes) VALUES(?,?,?,?,?,?,?,?)',(lid,domain,'Foundational competency below local review threshold','Small-group practice 3 times weekly; use concrete teaching-learning material; reassess in 14 days','Planned','2026-11-14','U1','Synthetic demo intervention; teacher must validate'))
 c.commit(); c.close()

expand_demo_panel()

class Login(BaseModel): email:str; password:str
class LearnerIn(BaseModel): id:Optional[str]=None; name:str; grade:int=Field(ge=1,le=8); school_id:str; gender:str='NA'; attendance:float=Field(ge=0,le=100); reading_score:float=Field(ge=0,le=100); numeracy_score:float=Field(ge=0,le=100)
class InterventionIn(BaseModel): learner_id:str; domain:str; gap:str; recommendation:str; due_date:Optional[str]=None; notes:str=''
class StatusIn(BaseModel): status:str; notes:str=''

@app.get('/api/health')
def health(): return {'status':'ok','service':'NIPUNSetu API','version':'3.4.0'}
@app.post('/api/auth/login')
def login(body:Login):
 c=conn(); u=c.execute('SELECT * FROM users WHERE email=?',(body.email,)).fetchone(); c.close()
 if not u or u['password']!=pw_hash(body.password): raise HTTPException(401,'Incorrect email or password')
 return {'access_token':token_for(u),'token_type':'bearer','user':{'id':u['id'],'name':u['name'],'email':u['email'],'role':u['role'],'school_id':u['school_id'],'district':u['district']}}
@app.get('/api/auth/me')
def me(u=Depends(current_user)): return u
@app.get('/api/dashboard')
def dashboard(u=Depends(current_user)):
 c=conn(); where=''; args=[]
 if u['role']=='teacher': where=' WHERE l.school_id=?'; args=[u['school_id']]
 total=c.execute('SELECT COUNT(*) FROM learners l'+where,args).fetchone()[0]
 rows=c.execute('SELECT l.* FROM learners l'+where,args).fetchall(); vals=[dict(x) for x in rows]
 assessed=[x for x in vals if x['reading_score'] is not None and x['numeracy_score'] is not None]
 at_risk=sum(1 for x in assessed if x['reading_score']<50 or x['numeracy_score']<45 or x['attendance']<75)
 avg_r=round(sum(x['reading_score'] for x in assessed)/max(len(assessed),1),1); avg_n=round(sum(x['numeracy_score'] for x in assessed)/max(len(assessed),1),1)
 interventions=c.execute("SELECT COUNT(*) FROM interventions i JOIN learners l ON l.id=i.learner_id"+(' WHERE l.school_id=?' if u['role']=='teacher' else ''),args).fetchone()[0]
 done=c.execute("SELECT COUNT(*) FROM interventions i JOIN learners l ON l.id=i.learner_id WHERE i.status='Completed'"+(' AND l.school_id=?' if u['role']=='teacher' else ''),args).fetchone()[0]
 schools=(1 if u['role']=='teacher' else c.execute('SELECT COUNT(*) FROM schools').fetchone()[0])
 by_grade=[]
 for g in range(1,6):
  group=[x for x in assessed if x['grade']==g]; by_grade.append({'grade':g,'learners':len(group),'reading':round(sum(x['reading_score'] for x in group)/max(len(group),1),1),'numeracy':round(sum(x['numeracy_score'] for x in group)/max(len(group),1),1)})
 c.close(); return {'learners':total,'at_risk':at_risk,'risk_rate':round(at_risk/max(total,1)*100,1),'avg_reading':avg_r,'avg_numeracy':avg_n,'interventions':interventions,'completed':done,'schools':1 if u['role']=='teacher' else schools,'by_grade':by_grade,'source_note':'Demonstration dataset; not official government statistics.'}
@app.get('/api/learners')
def learners(q:str='',grade:str|None=None,risk:str='all',limit:int=500,offset:int=0,u=Depends(current_user)):
 c=conn(); sql='SELECT l.*,s.name school_name FROM learners l JOIN schools s ON s.id=l.school_id WHERE 1=1'; args=[]
 if u['role']=='teacher': sql+=' AND l.school_id=?'; args.append(u['school_id'])
 if q: sql+=' AND (l.name LIKE ? OR l.id LIKE ?)'; args += [f'%{q}%',f'%{q}%']
 if grade not in (None,'','all','All','undefined','null'):
  try: grade_value=int(grade)
  except (TypeError,ValueError): c.close(); raise HTTPException(422,'Grade must be a number from 1 to 8')
  if grade_value<1 or grade_value>8: c.close(); raise HTTPException(422,'Grade must be between 1 and 8')
  sql+=' AND l.grade=?'; args.append(grade_value)
 if risk=='high': sql+=' AND l.reading_score IS NOT NULL AND l.numeracy_score IS NOT NULL AND (l.reading_score<50 OR l.numeracy_score<45 OR l.attendance<75)'
 sql+=' ORDER BY CASE WHEN l.reading_score IS NULL OR l.numeracy_score IS NULL THEN 1 ELSE 0 END,(l.reading_score+l.numeracy_score)/2 ASC LIMIT ? OFFSET ?'; args += [min(limit,1000),offset]
 data=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close()
 for x in data: x['risk']='Not assessed' if x['reading_score'] is None or x['numeracy_score'] is None else ('High' if x['reading_score']<50 or x['numeracy_score']<45 or x['attendance']<75 else ('Watch' if x['reading_score']<70 or x['numeracy_score']<65 else 'On track'))
 return {'items':data,'count':len(data)}
@app.post('/api/learners')
def add_learner(body:LearnerIn,u=Depends(current_user)):
 if u['role'] not in ['teacher','admin']: raise HTTPException(403,'Insufficient permissions')
 if u['role']=='teacher' and body.school_id!=u['school_id']: raise HTTPException(403,'You can only add learners to your school')
 lid=body.id or 'L'+secrets.token_hex(4).upper(); rl='Independent' if body.reading_score>=75 else ('Letter' if body.reading_score>=50 else 'Beginner'); nl='Grade-ready' if body.numeracy_score>=75 else ('Developing' if body.numeracy_score>=45 else 'Needs support')
 c=conn()
 try: c.execute('INSERT INTO learners(id,name,grade,school_id,gender,attendance,reading_level,numeracy_level,reading_score,numeracy_score) VALUES(?,?,?,?,?,?,?,?,?,?)',(lid,body.name,body.grade,body.school_id,body.gender,body.attendance,rl,nl,body.reading_score,body.numeracy_score)); log(c,u,'CREATE','learner',lid); c.commit()
 except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'Learner ID already exists')
 c.close(); return {'id':lid,'message':'Learner created'}
@app.get('/api/learners/{lid}')
def learner_detail(lid:str,u=Depends(current_user)):
 c=conn(); row=c.execute('SELECT l.*,s.name school_name,s.block,s.district FROM learners l JOIN schools s ON s.id=l.school_id WHERE l.id=?',(lid,)).fetchone()
 if not row: c.close(); raise HTTPException(404,'Learner not found')
 if u['role']=='teacher' and row['school_id']!=u['school_id']: c.close(); raise HTTPException(403,'Forbidden')
 assessments=[dict(x) for x in c.execute('SELECT * FROM assessments WHERE learner_id=? ORDER BY assessed_on DESC',(lid,)).fetchall()]; interventions=[dict(x) for x in c.execute('SELECT * FROM interventions WHERE learner_id=? ORDER BY created_at DESC',(lid,)).fetchall()]; c.close(); return {'learner':dict(row),'assessments':assessments,'interventions':interventions}
@app.post('/api/interventions')
def create_intervention(body:InterventionIn,u=Depends(current_user)):
 c=conn(); l=c.execute('SELECT * FROM learners WHERE id=?',(body.learner_id,)).fetchone()
 if not l: c.close(); raise HTTPException(404,'Learner not found')
 if u['role']=='teacher' and l['school_id']!=u['school_id']: c.close(); raise HTTPException(403,'Forbidden')
 cur=c.execute('INSERT INTO interventions(learner_id,domain,gap,recommendation,due_date,teacher_id,notes) VALUES(?,?,?,?,?,?,?)',(body.learner_id,body.domain,body.gap,body.recommendation,body.due_date,u['id'],body.notes)); iid=cur.lastrowid; log(c,u,'CREATE','intervention',iid); c.commit(); c.close(); return {'id':iid,'message':'Intervention added to action tracker'}
@app.patch('/api/interventions/{iid}')
def update_intervention(iid:int,body:StatusIn,u=Depends(current_user)):
 if body.status not in ['Planned','In progress','Completed','Deferred']: raise HTTPException(400,'Invalid status')
 c=conn(); row=c.execute('SELECT i.*,l.school_id FROM interventions i JOIN learners l ON l.id=i.learner_id WHERE i.id=?',(iid,)).fetchone()
 if not row: c.close(); raise HTTPException(404,'Intervention not found')
 if u['role']=='teacher' and row['school_id']!=u['school_id']: c.close(); raise HTTPException(403,'Forbidden')
 c.execute('UPDATE interventions SET status=?,notes=?,completed_at=CASE WHEN ?="Completed" THEN datetime("now") ELSE completed_at END WHERE id=?',(body.status,body.notes,body.status,iid)); log(c,u,'UPDATE','intervention',iid,body.status); c.commit(); c.close(); return {'message':'Intervention updated'}
@app.get('/api/interventions')
def interventions(status:str='all',u=Depends(current_user)):
 c=conn(); sql='SELECT i.*,l.name learner_name,l.grade,l.school_id,s.name school_name FROM interventions i JOIN learners l ON l.id=i.learner_id JOIN schools s ON s.id=l.school_id WHERE 1=1'; args=[]
 if u['role']=='teacher': sql+=' AND l.school_id=?'; args.append(u['school_id'])
 if status!='all': sql+=' AND i.status=?'; args.append(status)
 sql+=' ORDER BY i.created_at DESC'; rows=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close(); return {'items':rows}
@app.get('/api/schools')
def schools(u=Depends(current_user)):
 c=conn(); rows=[dict(x) for x in c.execute('SELECT s.*,COUNT(l.id) learners,ROUND(AVG(l.reading_score),1) reading,ROUND(AVG(l.numeracy_score),1) numeracy,ROUND(AVG(l.attendance),1) attendance FROM schools s LEFT JOIN learners l ON l.school_id=s.id GROUP BY s.id').fetchall()]; c.close()
 if u['role']=='teacher': rows=[x for x in rows if x['id']==u['school_id']]
 return {'items':rows}
@app.get('/api/governance')
def governance(u=Depends(current_user)):
 return {'canonical_fields':[{'field':'learner_id','type':'string','required':True,'description':'Pseudonymous learner identifier; never use Aadhaar.'},{'field':'school_id','type':'string','required':True,'description':'UDISE+ school code mapped to local school registry.'},{'field':'grade','type':'integer','required':True,'description':'Class/grade, normalised to integer.'},{'field':'assessment_domain','type':'enum','required':True,'description':'reading | numeracy; mapped from state assessment codes.'},{'field':'score','type':'number','required':True,'description':'Normalised 0–100 score; retain original scale in source metadata.'},{'field':'attendance_pct','type':'number','required':False,'description':'Attendance percentage over a declared reporting period.'},{'field':'assessment_date','type':'date','required':True,'description':'ISO-8601 date.'}], 'source_mappings':[{'source':'UDISE+','fields':'school_id, grade, enrolment, attendance','mode':'Approved aggregate/API or authorised export','status':'Connector design'},{'source':'PARAKH Rashtriya Sarvekshan','fields':'competency/domain aggregates','mode':'Published assessment aggregates','status':'Reference mapping'},{'source':'ASER','fields':'foundational reading/arithmetic levels','mode':'Survey aggregates; not learner-level linkage','status':'Reference mapping'},{'source':'State assessment systems','fields':'learner_id, score, domain, date','mode':'State-authorised CSV/API adapter','status':'CSV adapter demo'},{'source':'DIKSHA','fields':'teacher resources and content identifiers','mode':'Approved catalogue/API integration','status':'Planned'}], 'principles':['Purpose limitation and data minimisation','Role-based access and school/district boundaries','Pseudonymous learner IDs; no Aadhaar collection','Source lineage and import audit trail','Human-in-the-loop recommendations','Retention schedule and correction workflow','Encryption in transit and at rest in production'], 'disclaimer':'This prototype does not connect to government systems and must not be represented as an official UDISE+/PARAKH integration.'}
@app.post('/api/import/csv')
async def import_csv(file:UploadFile=File(...),u=Depends(current_user)):
 if u['role'] not in ['teacher','block_officer','state_admin','admin']: raise HTTPException(403,'Import not permitted')
 if not file.filename.lower().endswith('.csv'): raise HTTPException(400,'Upload a CSV file')
 raw=(await file.read()).decode('utf-8-sig'); reader=csv.DictReader(io.StringIO(raw)); required={'learner_id','name','grade','school_id','attendance_pct','reading_score','numeracy_score'}
 if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(400,'Required columns: '+', '.join(sorted(required)))
 c=conn(); added=0
 try:
  for r in reader:
   if u['role']=='teacher' and r['school_id']!=u['school_id']: continue
   if not c.execute('SELECT 1 FROM schools WHERE id=?',(r['school_id'],)).fetchone(): continue
   rs=float(r['reading_score']); ns=float(r['numeracy_score']); att=float(r['attendance_pct']); rl='Independent' if rs>=75 else ('Letter' if rs>=50 else 'Beginner'); nl='Grade-ready' if ns>=75 else ('Developing' if ns>=45 else 'Needs support')
   c.execute('INSERT INTO learners(id,name,grade,school_id,gender,attendance,reading_level,numeracy_level,reading_score,numeracy_score) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,grade=excluded.grade,attendance=excluded.attendance,reading_score=excluded.reading_score,numeracy_score=excluded.numeracy_score,reading_level=excluded.reading_level,numeracy_level=excluded.numeracy_level,updated_at=datetime("now")',(r['learner_id'],r['name'],int(r['grade']),r['school_id'],r.get('gender','NA'),att,rl,nl,rs,ns)); added+=1
  c.execute('INSERT INTO imports(filename,rows_added,source,imported_by) VALUES(?,?,?,?)',(file.filename,added,'CSV state assessment adapter',u['id'])); log(c,u,'IMPORT','learners',added,file.filename); c.commit()
 except Exception as e: c.rollback(); c.close(); raise HTTPException(400,f'CSV validation failed: {e}')
 c.close(); return {'rows_processed':added,'message':'Import complete; source lineage recorded'}

class ReassessmentIn(BaseModel):
 learner_id:str; domain:str; score:float=Field(ge=0,le=100); assessed_on:Optional[str]=None; intervention_id:Optional[int]=None; notes:str=''
class SyncBatch(BaseModel): events:list[dict]=Field(default_factory=list,max_length=100)

@app.post('/api/reassessments')
def add_reassessment(body:ReassessmentIn,u=Depends(current_user)):
 if body.domain not in ['reading','numeracy']: raise HTTPException(400,'Domain must be reading or numeracy')
 c=conn(); learner=c.execute('SELECT * FROM learners WHERE id=?',(body.learner_id,)).fetchone()
 if not learner: c.close(); raise HTTPException(404,'Learner not found')
 if u['role']=='teacher' and learner['school_id']!=u['school_id']: c.close(); raise HTTPException(403,'Forbidden')
 date=body.assessed_on or datetime.date.today().isoformat(); level=('Independent' if body.score>=75 else 'Letter' if body.score>=50 else 'Beginner') if body.domain=='reading' else ('Grade-ready' if body.score>=75 else 'Developing' if body.score>=45 else 'Needs support')
 c.execute('INSERT INTO reassessments(learner_id,domain,score,assessed_on,intervention_id,assessor,notes) VALUES(?,?,?,?,?,?,?)',(body.learner_id,body.domain,body.score,date,body.intervention_id,u['id'],body.notes))
 c.execute('INSERT INTO assessments(learner_id,domain,score,level,source,assessed_on,assessor) VALUES(?,?,?,?,?,?,?)',(body.learner_id,body.domain,body.score,level,'NIPUNSetu reassessment',date,u['id']))
 col='reading_score' if body.domain=='reading' else 'numeracy_score'; lvl='reading_level' if body.domain=='reading' else 'numeracy_level'
 c.execute(f'UPDATE learners SET {col}=?,{lvl}=?,updated_at=datetime("now") WHERE id=?',(body.score,level,body.learner_id)); log(c,u,'REASSESS','learner',body.learner_id,f'{body.domain}:{body.score}'); c.commit(); c.close()
 return {'message':'Reassessment saved','learner_id':body.learner_id,'domain':body.domain,'score':body.score,'previous_score':learner[col],'delta':round(body.score-learner[col],1) if learner[col] is not None else None,'level':level}

@app.get('/api/analytics/predictions')
def predictions(u=Depends(current_user)):
 c=conn(); sql='SELECT l.*,s.name school_name,s.block,s.district FROM learners l JOIN schools s ON s.id=l.school_id WHERE l.reading_score IS NOT NULL AND l.numeracy_score IS NOT NULL'; args=[]
 if u['role']=='teacher': sql+=' WHERE l.school_id=?'; args=[u['school_id']]
 rows=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close(); out=[]
 for x in rows:
  # Transparent heuristic risk score; not a trained or validated predictive model.
  score=max(0,min(100,round((100-x['reading_score'])*.35+(100-x['numeracy_score'])*.35+(100-x['attendance'])*.30,1)))
  if score>=55: band='High'; action='Immediate small-group intervention and fortnightly reassessment'
  elif score>=35: band='Watch'; action='Targeted practice twice weekly; review attendance'
  else: band='On track'; action='Continue classroom practice and monthly check'
  out.append({'learner_id':x['id'],'name':x['name'],'grade':x['grade'],'school':x['school_name'],'block':x['block'],'district':x['district'],'risk_score':score,'risk_band':band,'recommended_action':action})
 return {'model':'Transparent weighted risk heuristic v1','not_a_validated_prediction':True,'items':sorted(out,key=lambda z:z['risk_score'],reverse=True)}

@app.get('/api/analytics/ml-validation-legacy')
def ml_validation(u=Depends(current_user)):
 """Train/test a tiny logistic-regression baseline on synthetic proxy labels.
 This validates the engineering pipeline only, not real-world learner outcomes.
 """
 c=conn(); sql='SELECT l.id,l.grade,l.reading_score,l.numeracy_score,l.attendance FROM learners l'; args=[]
 if u['role']=='teacher': sql+=' WHERE l.school_id=?'; args=[u['school_id']]
 rows=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close()
 if len(rows)<20: raise HTTPException(400,'At least 20 learner records are required for a holdout validation')
 # Proxy label is deliberately explicit: the target is a synthetic threshold rule, not an observed future outcome.
 samples=[]
 for x in rows:
  feat=[x['reading_score']/100.0,x['numeracy_score']/100.0,x['attendance']/100.0,x['grade']/5.0]
  label=int(x['reading_score']<50 or x['numeracy_score']<45 or x['attendance']<75)
  samples.append((feat,label))
 train=[z for i,z in enumerate(samples) if i%5!=0]; test=[z for i,z in enumerate(samples) if i%5==0]
 if len({y for _,y in train})<2 or len({y for _,y in test})<2:
  train=samples[::2]; test=samples[1::2]
 w=[0.0]*4; b=0.0; lr=0.18; steps=2400
 def sigmoid(z):
  z=max(-30,min(30,z)); return 1/(1+__import__('math').exp(-z))
 for _ in range(steps):
  gw=[0.0]*4; gb=0.0
  for feat,y in train:
   p=sigmoid(sum(a*v for a,v in zip(w,feat))+b); err=p-y
   for j,v in enumerate(feat): gw[j]+=err*v
   gb+=err
  n=max(1,len(train))
  for j in range(4): w[j]-=lr*(gw[j]/n+0.001*w[j])
  b-=lr*gb/n
 tp=tn=fp=fn=0
 for feat,y in test:
  pred=int(sigmoid(sum(a*v for a,v in zip(w,feat))+b)>=0.5)
  if pred and y: tp+=1
  elif pred and not y: fp+=1
  elif not pred and y: fn+=1
  else: tn+=1
 accuracy=(tp+tn)/max(1,len(test)); precision=tp/max(1,tp+fp); recall=tp/max(1,tp+fn); f1=2*precision*recall/max(1e-9,precision+recall)
 return {'model':'Logistic regression · synthetic FLN risk proxy','algorithm':'Binary logistic regression trained with gradient descent; 4 normalised features','samples':len(samples),'train_samples':len(train),'test_samples':len(test),'positive_rate':round(sum(y for _,y in samples)/len(samples),3),'metrics':{'accuracy':round(accuracy,3),'precision':round(precision,3),'recall':round(recall,3),'f1':round(f1,3),'confusion_matrix':{'true_positive':tp,'false_positive':fp,'true_negative':tn,'false_negative':fn}},'features':['reading_score','numeracy_score','attendance_pct','grade'],'target_definition':'Synthetic proxy label: reading < 50 OR numeracy < 45 OR attendance < 75.','split':'Deterministic 80/20 holdout; fallback alternating split if class balance requires it.','limitations':['All rows are synthetic demonstration records.','Target is generated from the same assessment features, so metrics are not evidence of real-world predictive validity.','No child should be labelled, denied services or disciplined by this score; human review is mandatory.'],'validation_status':'Pipeline smoke-validated on synthetic proxy labels only; external validation with authorised longitudinal outcomes is required.'}

@app.get('/api/analytics/cohorts')
def cohort_analytics(u=Depends(current_user)):
 c=conn(); sql="SELECT s.block,s.district,l.grade,COUNT(*) learners,ROUND(AVG(l.reading_score),1) reading,ROUND(AVG(l.numeracy_score),1) numeracy,ROUND(AVG(l.attendance),1) attendance FROM learners l JOIN schools s ON s.id=l.school_id"
 args=[]
 if u['role']=='teacher': sql+=' WHERE l.school_id=?'; args=[u['school_id']]
 sql+=' GROUP BY s.block,s.district,l.grade ORDER BY s.block,l.grade'
 rows=[dict(r) for r in c.execute(sql,args).fetchall()]
 c.close()
 for r in rows:
  r['priority_index']=round((100-(r['reading'] or 0))*.4+(100-(r['numeracy'] or 0))*.4+(100-(r['attendance'] or 0))*.2,1)
 return {'cohorts':rows,'method':'Descriptive cohort aggregation; no causal claim.','synthetic_data':True}

@app.get('/api/analytics/impact')
def impact_analytics(u=Depends(current_user)):
 c=conn(); sql="SELECT a.learner_id,a.domain,MIN(a.score) baseline,MAX(a.score) latest,COUNT(*) observations FROM assessments a JOIN learners l ON l.id=a.learner_id"
 args=[]
 if u['role']=='teacher': sql+=' WHERE l.school_id=?'; args=[u['school_id']]
 sql+=' GROUP BY a.learner_id,a.domain HAVING COUNT(*)>=2'
 rows=[dict(r) for r in c.execute(sql,args).fetchall()]; c.close()
 deltas=[r['latest']-r['baseline'] for r in rows]
 return {'domains':{d:{'pairs':sum(1 for r in rows if r['domain']==d),'mean_change':round(sum(r['latest']-r['baseline'] for r in rows if r['domain']==d)/max(1,sum(1 for r in rows if r['domain']==d)),1)} for d in ['reading','numeracy']},'learner_domain_pairs':len(rows),'mean_change_all':round(sum(deltas)/max(1,len(deltas)),1),'warning':'Synthetic demo history; observed change is not causal impact and must not be attributed to an intervention without a valid evaluation design.','synthetic_data':True}

@app.get('/api/maps/administrative')
def administrative_map(u=Depends(current_user)):
 c=conn(); rows=[dict(x) for x in c.execute('SELECT s.id,s.name,s.block,s.district,s.state,s.udise_code,s.data_origin,COUNT(l.id) learners,ROUND(AVG(l.reading_score),1) reading,ROUND(AVG(l.numeracy_score),1) numeracy,ROUND(AVG(l.attendance),1) attendance FROM schools s LEFT JOIN learners l ON l.school_id=s.id GROUP BY s.id').fetchall()]; c.close()
 if u['role']=='teacher': rows=[x for x in rows if x['id']==u['school_id']]
 for x in rows: x['risk_rate']=round(sum(1 for y in [] ) if not x['learners'] else max(0,100-((x['reading'] or 0)+(x['numeracy'] or 0))/2),1)
 return {'items':rows,'geometry':'School points are illustrative; geocodes must come from authorised UDISE+ master data.','note':'No fabricated coordinates are supplied.'}

@app.get('/api/resources')
def diksha_resources(domain:str='all',language:str='all',grade:str|None=None,u=Depends(current_user)):
 catalogue=[
 {'id':'R01','title':'Sound-letter mapping and phonemic awareness','domain':'reading','grade_min':1,'grade_max':2,'language':'hi','format':'Teacher-led oral activity','duration_min':15,'competency':'Decode familiar letters and sounds'},
 {'id':'R02','title':'Recognise and read familiar words','domain':'reading','grade_min':1,'grade_max':2,'language':'hi','format':'Flash cards / word wall','duration_min':15,'competency':'Read familiar words with accuracy'},
 {'id':'R03','title':'Read a short paragraph fluently','domain':'reading','grade_min':2,'grade_max':3,'language':'hi','format':'Guided repeated reading','duration_min':20,'competency':'Read grade-appropriate text'},
 {'id':'R04','title':'Listen, retell and answer comprehension questions','domain':'reading','grade_min':2,'grade_max':4,'language':'hi','format':'Story circle','duration_min':20,'competency':'Demonstrate listening comprehension'},
 {'id':'R05','title':'Sentence construction with picture prompts','domain':'reading','grade_min':2,'grade_max':4,'language':'en','format':'Worksheet / peer activity','duration_min':20,'competency':'Construct meaningful sentences'},
 {'id':'R06','title':'Read and interpret a simple informational text','domain':'reading','grade_min':3,'grade_max':5,'language':'en','format':'Paired reading','duration_min':25,'competency':'Extract explicit information'},
 {'id':'R07','title':'Vocabulary building through local context','domain':'reading','grade_min':1,'grade_max':5,'language':'hi','format':'Classroom discussion','duration_min':15,'competency':'Build contextual vocabulary'},
 {'id':'R08','title':'Reading fluency: accuracy, pace and expression','domain':'reading','grade_min':3,'grade_max':5,'language':'hi','format':'Fluency practice','duration_min':20,'competency':'Improve oral reading fluency'},
 {'id':'R09','title':'Number recognition and counting objects','domain':'numeracy','grade_min':1,'grade_max':2,'language':'hi','format':'Counters / stones / sticks','duration_min':15,'competency':'Count and represent quantities'},
 {'id':'R10','title':'Compare and order two-digit numbers','domain':'numeracy','grade_min':1,'grade_max':3,'language':'hi','format':'Number cards','duration_min':15,'competency':'Understand place value'},
 {'id':'R11','title':'Addition using grouping and number bonds','domain':'numeracy','grade_min':1,'grade_max':3,'language':'hi','format':'Low-cost TLM activity','duration_min':20,'competency':'Add within grade-appropriate range'},
 {'id':'R12','title':'Subtraction on an open number line','domain':'numeracy','grade_min':2,'grade_max':4,'language':'en','format':'Number-line practice','duration_min':20,'competency':'Subtract using number relationships'},
 {'id':'R13','title':'Multiplication as equal groups and arrays','domain':'numeracy','grade_min':2,'grade_max':4,'language':'hi','format':'Counters / array cards','duration_min':20,'competency':'Understand multiplication conceptually'},
 {'id':'R14','title':'Division as sharing and grouping','domain':'numeracy','grade_min':3,'grade_max':5,'language':'hi','format':'Manipulative activity','duration_min':20,'competency':'Understand division as equal sharing'},
 {'id':'R15','title':'Fractions using paper folding','domain':'numeracy','grade_min':3,'grade_max':5,'language':'en','format':'Hands-on activity','duration_min':25,'competency':'Represent simple fractions'},
 {'id':'R16','title':'Measurement with non-standard units','domain':'numeracy','grade_min':2,'grade_max':4,'language':'hi','format':'Classroom measurement walk','duration_min':20,'competency':'Estimate and measure length'},
 {'id':'R17','title':'Recognise patterns and extend sequences','domain':'numeracy','grade_min':1,'grade_max':4,'language':'en','format':'Pattern cards','duration_min':15,'competency':'Identify and extend patterns'},
 {'id':'R18','title':'Read simple tables and pictographs','domain':'numeracy','grade_min':3,'grade_max':5,'language':'en','format':'Data interpretation activity','duration_min':20,'competency':'Interpret simple data displays'},
 {'id':'R19','title':'Attendance conversation and family follow-up guide','domain':'wellbeing','grade_min':1,'grade_max':5,'language':'hi','format':'Teacher-family engagement','duration_min':10,'competency':'Identify barriers to regular attendance'},
 {'id':'R20','title':'Multilingual classroom read-aloud routine','domain':'reading','grade_min':1,'grade_max':5,'language':'hi','format':'Teacher facilitation guide','duration_min':15,'competency':'Build language confidence'}]
 # Additional locally usable activities; all are clearly labelled as teacher-use activity plans,
 # while links point to the official DIKSHA FLN discovery page rather than fabricated content IDs.
 extras=[
 ('Picture walk: predict the story','reading',1,2,'hi','Picture cards / oral discussion','Use illustrations to predict events'),('Syllable clapping and word segmentation','reading',1,3,'hi','Clap, tap and say','Hear syllables in familiar words'),('Beginning-middle-end story sequencing','reading',2,3,'hi','Three-picture sequence','Retell events in logical order'),('Who, what, where comprehension','reading',2,4,'hi','Question cards','Answer literal comprehension questions'),('Read a short instruction and do it','reading',2,4,'en','Instruction cards','Read and follow simple written directions'),('Paired echo reading','reading',2,5,'hi','Peer reading','Improve accuracy through supported reading'),('Common-word bingo','reading',1,3,'hi','Word cards','Recognise high-frequency words'),('Build a sentence from word cards','reading',2,4,'en','Word cards','Order words into a meaningful sentence'),('Punctuation pause practice','reading',3,5,'hi','Short passage','Use punctuation to support fluency'),('Retell a local folk tale','reading',1,5,'hi','Oral storytelling','Sequence and retell narrative information'),('Read a timetable','reading',3,5,'en','Sample timetable','Locate explicit information in a table'),('Prefix and suffix word families','reading',3,5,'hi','Word-family chart','Notice patterns in word formation'),('Count forward and backward from a number','numeracy',1,2,'hi','Number line','Count in sequence from varied start points'),('Make ten: number bonds','numeracy',1,2,'hi','Ten frames / seeds','Compose and decompose numbers to ten'),('Compare quantities: more, less, equal','numeracy',1,2,'hi','Counters','Compare two sets and explain'),('Place-value bundle sticks','numeracy',2,3,'hi','Sticks / rubber bands','Group ones into tens'),('Addition story problems','numeracy',2,3,'hi','Local context cards','Model addition in a real situation'),('Subtraction as take-away and difference','numeracy',2,3,'hi','Counters / number line','Distinguish subtraction meanings'),('Skip counting with movement','numeracy',2,4,'hi','Floor number line','Count in equal intervals'),('Multiplication array drawing','numeracy',3,4,'en','Grid paper','Connect arrays to multiplication facts'),('Division sharing with seeds','numeracy',3,4,'hi','Seeds / bottle caps','Share equally and identify remainder'),('Equivalent fractions with paper strips','numeracy',4,5,'en','Paper strips','Recognise simple equivalent fractions'),('Money: make the exact amount','numeracy',3,5,'hi','Play currency','Combine denominations to make a total'),('Time: read an analogue clock','numeracy',2,4,'hi','Clock face','Read o’clock and half-hour times'),('Length estimation and comparison','numeracy',2,4,'en','Classroom objects','Estimate, compare and measure length'),('Mass: heavier and lighter','numeracy',2,4,'hi','Balance / objects','Compare mass using direct comparison'),('Shape hunt around the school','numeracy',1,3,'hi','Shape checklist','Identify 2D and 3D shapes in context'),('Pattern rule detective','numeracy',2,5,'en','Pattern cards','Describe and extend a repeating pattern'),('Data tally from classroom survey','numeracy',3,5,'hi','Tally sheet','Collect and represent simple data'),('Word problems: choose the operation','numeracy',3,5,'en','Problem cards','Select operation based on context'),('Estimate then calculate','numeracy',4,5,'hi','Number cards','Use estimation to check reasonableness'),('Attendance barrier conversation guide','wellbeing',1,5,'hi','Family conversation guide','Identify attendance barriers without blame'),('Inclusive multi-sensory phonics routine','reading',1,3,'hi','Sound cards / tactile letters','Provide multiple ways to practise phonics'),('Small-group formative assessment checklist','assessment',1,5,'en','Teacher checklist','Record observable competency evidence'),('Exit-ticket: one-minute number sense','assessment',1,5,'hi','Mini whiteboard / paper','Check understanding at lesson end'),('Read-aloud: pause, predict, discuss','reading',1,4,'hi','Storybook','Develop listening and comprehension'),('Math talk: explain your strategy','numeracy',2,5,'hi','Peer discussion','Explain mathematical reasoning'),('Peer tutoring rotation','teaching-practice',1,5,'en','Rotating pairs','Structure short supported practice'),('Error analysis with worked examples','numeracy',3,5,'en','Worked examples','Identify and correct common misconceptions'),('Fluency progress monitoring sheet','assessment',1,5,'hi','Teacher recording sheet','Track repeated reading observations'),('Learning recovery weekly planning template','teaching-practice',1,5,'en','Weekly plan','Plan grouping, practice and reassessment')]
 for i,(title,dom,gmin,gmax,lang,fmt,comp) in enumerate(extras,21):
  catalogue.append({'id':f'R{i:02d}','title':title,'domain':dom,'grade_min':gmin,'grade_max':gmax,'language':lang,'format':fmt,'duration_min':15 if i%3 else 20,'competency':comp,'source_type':'Teacher activity plan'})
 for x in catalogue:
  x.setdefault('source_type','Curated classroom activity')
  x['url']='https://diksha.gov.in/fln.html'
 if grade not in (None,''):
  try: grade_value=int(grade)
  except (TypeError,ValueError): raise HTTPException(422,'Grade must be a number from 1 to 8')
  if grade_value<1 or grade_value>8: raise HTTPException(422,'Grade must be between 1 and 8')
 else: grade_value=None
 items=[x for x in catalogue if (domain=='all' or x['domain']==domain) and (language=='all' or x['language']==language) and (grade_value is None or x['grade_min']<=grade_value<=x['grade_max'])]
 return {'items':items,'count':len(items),'integration_status':'60 competency-aligned classroom activity plans. Official DIKSHA FLN discovery link supplied; no live catalogue API or item-level availability is claimed.','source_note':'Activities are curated for demonstration and teacher adaptation. Confirm state curriculum, language and learner level before use.','official_reference':'https://diksha.gov.in/fln.html'}


@app.post('/api/sync/batch')
def sync_batch(body:SyncBatch,u=Depends(current_user)):
 c=conn(); accepted=[]
 for ev in body.events:
  eid=str(ev.get('id',''))
  if not eid or len(eid)>100: continue
  cur=c.execute('INSERT OR IGNORE INTO sync_events(id,user_id,event_type,payload) VALUES(?,?,?,?)',(eid,u['id'],str(ev.get('type','unknown'))[:60],json.dumps(ev.get('payload',{}))))
  if cur.rowcount: accepted.append(eid)
 c.commit(); c.close(); return {'accepted':accepted,'accepted_count':len(accepted),'idempotent':True}

@app.get('/api/progress/{lid}')
def learner_progress(lid:str,u=Depends(current_user)):
 c=conn(); l=c.execute('SELECT * FROM learners WHERE id=?',(lid,)).fetchone()
 if not l: c.close(); raise HTTPException(404,'Learner not found')
 if u['role']=='teacher' and l['school_id']!=u['school_id']: c.close(); raise HTTPException(403,'Forbidden')
 rows=[dict(x) for x in c.execute('SELECT domain,score,assessed_on,source FROM assessments WHERE learner_id=? ORDER BY assessed_on,id',(lid,)).fetchall()]; c.close(); return {'learner_id':lid,'history':rows}

@app.get('/api/audit')
def audit(u=Depends(current_user)):
 if u['role'] not in ['block_officer','state_admin','admin']: raise HTTPException(403,'Audit access restricted')
 c=conn(); rows=[dict(x) for x in c.execute('SELECT a.*,u.name actor FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 100').fetchall()]; c.close(); return {'items':rows}
@app.get('/api/export/learners')
def export_learners(u=Depends(current_user)):
 data=learners(q='',limit=1000,offset=0,u=u)['items']; return {'schema_version':'1.0','exported_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source':'NIPUNSetu demonstration database','records':data}

from .v33 import router as v33_router, init_store as init_v33_store
app.include_router(v33_router)
init_v33_store()

from .v34 import router as v34_router, init_store as init_v34_store
app.include_router(v34_router)
init_v34_store()

from .v36 import router as v36_router, init_store as init_v36_store
app.include_router(v36_router)
init_v36_store()
