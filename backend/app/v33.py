"""NIPUNSetu v3.3: provenance-aware assessment ingestion and outcome analytics."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header, Form
import csv, io, json, secrets, datetime, math, hashlib

router = APIRouter()

def get_user(authorization: str | None = Header(None)):
    from . import main as m
    return m.current_user(authorization)

def init_store():
    from . import main as m
    c=m.conn()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS assessment_observations(
      id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT NOT NULL, school_id TEXT NOT NULL,
      grade INTEGER NOT NULL, domain TEXT NOT NULL, competency_code TEXT NOT NULL,
      score REAL NOT NULL CHECK(score>=0 AND score<=100), attendance_pct REAL,
      assessed_on TEXT NOT NULL, source_system TEXT NOT NULL, source_record_id TEXT NOT NULL,
      import_batch_id TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(source_system,source_record_id));
    CREATE INDEX IF NOT EXISTS idx_obs_cohort ON assessment_observations(school_id,grade,domain,competency_code,assessed_on);
    CREATE INDEX IF NOT EXISTS idx_obs_learner ON assessment_observations(learner_id,domain,assessed_on);
    CREATE TABLE IF NOT EXISTS assessment_import_batches(
      id TEXT PRIMARY KEY,filename TEXT,source_system TEXT,imported_by TEXT,total_rows INTEGER,
      accepted_rows INTEGER,rejected_rows INTEGER,status TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS assessment_import_errors(
      id INTEGER PRIMARY KEY AUTOINCREMENT,batch_id TEXT,row_number INTEGER,learner_id TEXT,reason TEXT,raw_row TEXT);
    ''')
    batch_cols={r[1] for r in c.execute('PRAGMA table_info(assessment_import_batches)').fetchall()}
    if 'authorisation_reference' not in batch_cols: c.execute('ALTER TABLE assessment_import_batches ADD COLUMN authorisation_reference TEXT')
    legacy=c.execute('''SELECT a.learner_id,l.school_id,l.grade,a.domain,a.score,a.assessed_on,a.source,l.attendance
      FROM assessments a JOIN learners l ON l.id=a.learner_id ORDER BY a.assessed_on,a.id''').fetchall()
    for r in legacy:
        comp='FLN-READ-GEN' if r['domain']=='reading' else 'FLN-NUM-GEN'
        rid=f"legacy-{r['learner_id']}-{r['domain']}-{r['assessed_on']}"
        c.execute('''INSERT OR IGNORE INTO assessment_observations
          (learner_id,school_id,grade,domain,competency_code,score,attendance_pct,assessed_on,source_system,source_record_id)
          VALUES(?,?,?,?,?,?,?,?,?,?)''',(r['learner_id'],r['school_id'],r['grade'],r['domain'],comp,r['score'],r['attendance'],r['assessed_on'],r['source'] or 'legacy-demo',rid))
    c.commit(); c.close()

@router.get('/api/import/template')
def import_template(u=Depends(get_user)):
    return {'schema_version':'2.0','required_columns':['learner_id','school_udise_code','grade','assessment_date','domain','competency_code','score','source_system','source_record_id'],'optional_columns':['attendance_pct'],'example':{'learner_id':'PSEUDO-0001','school_udise_code':'09100403001','grade':'3','assessment_date':'2026-10-15','domain':'reading','competency_code':'FLN-RD-WORD-01','score':'62','attendance_pct':'86','source_system':'STATE_ASSESSMENT_EXPORT','source_record_id':'row-0001'},'privacy':['Use state-approved pseudonymous learner IDs, never Aadhaar or child names.','Upload only data covered by an authorised sharing basis.','ASER/PARAKH aggregate data must not be converted into learner-level records.']}

@router.post('/api/import/state-assessment')
async def import_state_assessment(file:UploadFile=File(...), source_system:str='STATE_ASSESSMENT_EXPORT', authorisation_reference:str=Form(''), u=Depends(get_user)):
    from . import main as m
    if u['role'] not in ('block_officer','state_admin','admin'): raise HTTPException(403,'Assessment imports are restricted to authorised block/state/admin roles')
    if not authorisation_reference.strip(): raise HTTPException(422,'Provide the data-sharing approval/reference ID. Demo data must not be marked as authorised.')
    if not file.filename.lower().endswith('.csv'): raise HTTPException(400,'Upload a CSV file')
    raw=await file.read()
    if len(raw)>10*1024*1024: raise HTTPException(413,'CSV exceeds 10 MB')
    try: reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    except UnicodeDecodeError: raise HTTPException(400,'CSV must be UTF-8')
    required={'learner_id','school_udise_code','grade','assessment_date','domain','competency_code','score','source_system','source_record_id'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(422,{'message':'CSV schema mismatch','missing':sorted(required-set(reader.fieldnames or []))})
    batch=secrets.token_hex(12); c=m.conn(); accepted=rejected=seen=0
    for rowno,row in enumerate(reader,2):
        seen+=1
        try:
            lid=(row.get('learner_id') or '').strip(); udise=(row.get('school_udise_code') or '').strip(); grade=int(row.get('grade',''))
            domain=(row.get('domain') or '').strip().lower(); competency=(row.get('competency_code') or '').strip(); score=float(row.get('score',''))
            date=(row.get('assessment_date') or '').strip(); datetime.date.fromisoformat(date)
            src=(row.get('source_system') or source_system).strip()[:80]; record=(row.get('source_record_id') or '').strip()
            if not lid or not competency or not record: raise ValueError('learner_id, competency_code and source_record_id are required')
            if grade not in range(1,9): raise ValueError('grade must be 1–8')
            if domain not in ('reading','numeracy'): raise ValueError('domain must be reading or numeracy')
            if not 0<=score<=100: raise ValueError('score must be 0–100')
            school=c.execute('SELECT id FROM schools WHERE udise_code=?',(udise,)).fetchone()
            learner=c.execute('SELECT id,school_id,grade FROM learners WHERE id=?',(lid,)).fetchone()
            if not school: raise ValueError('UDISE code not mapped in school master')
            if not learner: raise ValueError('Pseudonymous learner ID not mapped; import authorised roster first')
            if learner['school_id']!=school['id'] or learner['grade']!=grade: raise ValueError('Learner-school-grade mapping mismatch')
            a=(row.get('attendance_pct') or '').strip(); attendance=float(a) if a else None
            if attendance is not None and not 0<=attendance<=100: raise ValueError('attendance_pct must be 0–100')
            c.execute('''INSERT OR IGNORE INTO assessment_observations
              (learner_id,school_id,grade,domain,competency_code,score,attendance_pct,assessed_on,source_system,source_record_id,import_batch_id)
              VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(lid,school['id'],grade,domain,competency,score,attendance,date,src,record,batch))
            if c.execute('SELECT changes()').fetchone()[0]: accepted+=1
        except Exception as e:
            rejected+=1; c.execute('INSERT INTO assessment_import_errors(batch_id,row_number,learner_id,reason,raw_row) VALUES(?,?,?,?,?)',(batch,rowno,(row or {}).get('learner_id',''),str(e)[:250],json.dumps(row)))
    status='completed' if rejected==0 else ('partial' if accepted else 'rejected')
    c.execute('INSERT INTO assessment_import_batches(id,filename,source_system,imported_by,total_rows,accepted_rows,rejected_rows,status,authorisation_reference) VALUES(?,?,?,?,?,?,?,?,?)',(batch,file.filename,source_system,u['id'],seen,accepted,rejected,status,authorisation_reference[:120]))
    m.log(c,u,'IMPORT','assessment_batch',batch,f'{accepted} accepted; {rejected} rejected'); c.commit()
    errors=[dict(x) for x in c.execute('SELECT row_number,learner_id,reason FROM assessment_import_errors WHERE batch_id=? ORDER BY row_number LIMIT 50',(batch,)).fetchall()]
    c.close()
    return {'batch_id':batch,'status':status,'total_rows':seen,'accepted_rows':accepted,'rejected_rows':rejected,'duplicates_ignored':max(0,seen-accepted-rejected),'errors':errors,'lineage':{'source_system':source_system,'filename':file.filename,'imported_by':u['id']},'note':'Source-attributed import only; no live government connector is implied.'}

@router.get('/api/import/batches')
def import_batches(u=Depends(get_user)):
    from . import main as m
    if u['role']=='teacher': raise HTTPException(403,'Import audit is restricted')
    c=m.conn(); rows=[dict(x) for x in c.execute('SELECT * FROM assessment_import_batches ORDER BY created_at DESC LIMIT 100').fetchall()]; c.close(); return {'items':rows}

@router.get('/api/analytics/competency-outcomes')
def competency_outcomes(u=Depends(get_user)):
    from . import main as m
    c=m.conn()
    sql='''SELECT o.school_id,s.name school_name,s.block,o.grade,o.domain,o.competency_code,o.learner_id,o.score,o.assessed_on
      FROM assessment_observations o JOIN schools s ON s.id=o.school_id'''; args=[]
    if u['role']=='teacher': sql+=' WHERE o.school_id=?'; args.append(u['school_id'])
    rows=[dict(x) for x in c.execute(sql+' ORDER BY o.learner_id,o.competency_code,o.assessed_on',args).fetchall()]; c.close()
    pairs={}
    for r in rows: pairs.setdefault((r['school_id'],r['grade'],r['domain'],r['competency_code'],r['learner_id']),[]).append(r)
    groups={}
    for key,vals in pairs.items():
        if len(vals)<2: continue
        first,last=vals[0],vals[-1]; k=(first['school_id'],first['school_name'],first['block'],first['grade'],first['domain'],first['competency_code'])
        g=groups.setdefault(k,{'n':0,'base':0,'latest':0,'up':0,'down':0}); g['n']+=1; g['base']+=first['score']; g['latest']+=last['score']; g['up']+=last['score']>first['score']; g['down']+=last['score']<first['score']
    out=[]
    for k,g in groups.items():
        n=g['n']; out.append({'school_id':k[0],'school':k[1],'block':k[2],'grade':k[3],'domain':k[4],'competency_code':k[5],'learners':n,'baseline_mean':round(g['base']/n,1),'latest_mean':round(g['latest']/n,1),'mean_change':round((g['latest']-g['base'])/n,1),'improved_share':round(g['up']/n*100,1),'declined_share':round(g['down']/n*100,1)})
    return {'items':sorted(out,key=lambda x:(x['mean_change'],x['learners']),reverse=True),'count':len(out),'method':'Paired earliest-to-latest learner observations within the same competency; descriptive, non-causal.','data_note':'Synthetic legacy observations and authorised imported observations are source-attributed; compare only like-for-like competency scales.'}

@router.get('/api/analytics/ml-validation')
def ml_validation(u=Depends(get_user)):
    """Leakage-aware engineering validation: future observations from unseen schools."""
    from . import main as m
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, brier_score_loss, confusion_matrix, roc_auc_score
    except Exception:
        return {'status':'dependency_missing','message':'Install backend requirements to enable ML validation.'}
    c=m.conn()
    sql="SELECT o.learner_id,o.school_id,o.grade,o.domain,o.competency_code,o.score,o.attendance_pct,o.assessed_on FROM assessment_observations o JOIN learners l ON l.id=o.learner_id JOIN assessment_import_batches b ON b.id=o.import_batch_id WHERE b.authorisation_reference IS NOT NULL AND b.authorisation_reference!=''"
    args=[]
    if u['role']=='teacher': sql+=' WHERE o.school_id=?'; args.append(u['school_id'])
    rows=[dict(x) for x in c.execute(sql+' ORDER BY o.assessed_on,o.id',args).fetchall()]; c.close()
    histories={}
    for r in rows: histories.setdefault((r['learner_id'],r['school_id'],r['grade'],r['domain'],r['competency_code']),[]).append(r)
    pairs=[]
    for key,h in histories.items():
        if len(h)<2: continue
        h=sorted(h,key=lambda x:x['assessed_on']); a,b=h[0],h[1]
        try: days=(datetime.date.fromisoformat(b['assessed_on'])-datetime.date.fromisoformat(a['assessed_on'])).days
        except Exception: continue
        if days<14 or a.get('attendance_pct') is None: continue
        pairs.append({'school':key[1],'baseline_date':a['assessed_on'],'outcome_date':b['assessed_on'],'x':[float(a['score']),float(a['attendance_pct']),float(a['grade']),1.0 if a['domain']=='reading' else 0.0],'y':int(float(b['score'])-float(a['score'])>=8)})
    if len(pairs)<40:
        return {'model':'Prospective learning-gain classifier','status':'insufficient_data','samples':len(pairs),'required_samples':40,'message':'Need at least 40 valid learner-domain-competency pairs with baseline attendance and a follow-up at least 14 days later.','split':'Unseen-school holdout AND future-outcome time holdout; no metrics until both conditions and class balance are met.'}
    dates=sorted(x['outcome_date'] for x in pairs); cutoff=dates[int(len(dates)*0.7)]
    schools=sorted({x['school'] for x in pairs}); held={sid for sid in schools if int(hashlib.sha256(sid.encode()).hexdigest()[:8],16)%5==0}
    if not held and len(schools)>1: held={schools[-1]}
    train=[x for x in pairs if x['school'] not in held and x['outcome_date']<=cutoff]
    test=[x for x in pairs if x['school'] in held and x['baseline_date']>=cutoff and x['outcome_date']>cutoff]
    if len(train)<20 or len(test)<10 or len({x['y'] for x in train})<2 or len({x['y'] for x in test})<2:
        return {'model':'Prospective learning-gain classifier','status':'insufficient_temporal_school_holdout','samples':len(pairs),'train_samples':len(train),'test_samples':len(test),'held_out_schools':sorted(held),'time_cutoff':cutoff,'message':'Insufficient observations in the unseen-school AND future-time test window with both target classes. Import more terms and schools; do not weaken the split.','validation_protocol':'Train on earlier outcomes from non-held-out schools; test on later outcomes from held-out schools.'}
    X=[x['x'] for x in train]; y=[x['y'] for x in train]; Xt=[x['x'] for x in test]; yt=[x['y'] for x in test]
    model=make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',max_iter=2000,random_state=42)); model.fit(X,y)
    probs=model.predict_proba(Xt)[:,1]; pred=(probs>=0.5).astype(int); cm=confusion_matrix(yt,pred,labels=[0,1]); majority=max(sum(yt),len(yt)-sum(yt))/len(yt)
    try: auc=roc_auc_score(yt,probs)
    except Exception: auc=None
    acc=float(accuracy_score(yt,pred))
    return {'model':'Prospective learning-gain classifier','algorithm':'StandardScaler + class-weighted logistic regression','status':'evaluated','samples':len(pairs),'train_samples':len(train),'test_samples':len(test),'held_out_schools':sorted(held),'time_cutoff':cutoff,'target_definition':'At least +8 score points between first two observations for same learner-domain-competency pair, separated by >=14 days.','metrics':{'accuracy':round(acc,3),'precision':round(float(precision_score(yt,pred,zero_division=0)),3),'recall':round(float(recall_score(yt,pred,zero_division=0)),3),'f1':round(float(f1_score(yt,pred,zero_division=0)),3),'brier_score':round(float(brier_score_loss(yt,probs)),3),'roc_auc':round(float(auc),3) if auc is not None else None,'majority_class_baseline_accuracy':round(float(majority),3),'beats_majority_baseline':acc>majority,'confusion_matrix':{'true_negative':int(cm[0,0]),'false_positive':int(cm[0,1]),'false_negative':int(cm[1,0]),'true_positive':int(cm[1,1])}},'split':'Strict dual holdout: earlier outcomes from non-held-out schools for training; later outcomes from held-out schools for testing.','features':['baseline_score','baseline_attendance_pct','grade','domain_indicator'],'limitations':['Engineering validation only until authorised real-world data is imported.','Observed gain is not causal intervention impact.','No PARAKH/ASER individual records are used or inferred.','Human review required; predictions must never deny services.'],'validation_status':'Real-world validity remains unestablished until imported batches are independently verified as authorised, non-synthetic state assessment data.'}

@router.get('/api/analytics/intervention-effectiveness')
def intervention_effectiveness(u=Depends(get_user)):
    from . import main as m
    c=m.conn()
    sql='''SELECT r.learner_id,r.domain,r.score after_score,r.assessed_on,r.intervention_id,i.created_at,l.school_id,s.block
      FROM reassessments r JOIN interventions i ON i.id=r.intervention_id JOIN learners l ON l.id=r.learner_id JOIN schools s ON s.id=l.school_id WHERE r.intervention_id IS NOT NULL'''; args=[]
    if u['role']=='teacher': sql+=' AND l.school_id=?'; args.append(u['school_id'])
    rows=[dict(x) for x in c.execute(sql,args).fetchall()]; paired=[]
    for row in rows:
        before=c.execute('SELECT score FROM assessments WHERE learner_id=? AND domain=? AND assessed_on<=date(?) ORDER BY assessed_on DESC,id DESC LIMIT 1',(row['learner_id'],row['domain'],row['created_at'][:10])).fetchone()
        if before: row['change']=round(row['after_score']-before['score'],1); paired.append(row)
    c.close(); groups={}
    for row in paired:
        key=(row['block'],row['domain']); g=groups.setdefault(key,{'block':key[0],'domain':key[1],'n':0,'sum':0,'positive':0}); g['n']+=1; g['sum']+=row['change']; g['positive']+=row['change']>0
    return {'items':[{'block':g['block'],'domain':g['domain'],'reassessments':g['n'],'mean_change':round(g['sum']/g['n'],1),'positive_change_share':round(g['positive']/g['n']*100,1)} for g in groups.values()],'paired_records':len(paired),'warning':'Before-after change is descriptive. A comparison group and pre-specified evaluation design are required for causal claims.'}

@router.post('/api/import/school-master')
async def import_school_master(file:UploadFile=File(...), source_system:str='UDISE_PLUS_PUBLIC_OR_AUTHORISED_EXPORT', u=Depends(get_user)):
    """Upsert school master metadata; accepts only source-attributed school directory rows."""
    from . import main as m
    if u['role'] not in ('block_officer','state_admin','admin'): raise HTTPException(403,'School master imports are restricted')
    raw=await file.read()
    if len(raw)>5*1024*1024: raise HTTPException(413,'CSV exceeds 5 MB')
    try: reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    except UnicodeDecodeError: raise HTTPException(400,'CSV must be UTF-8')
    required={'school_udise_code','school_name','block','district','state'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(422,{'missing':sorted(required-set(reader.fieldnames or []))})
    c=m.conn(); added=updated=rejected=0; errors=[]
    for rn,row in enumerate(reader,2):
        try:
            code=row['school_udise_code'].strip(); name=row['school_name'].strip(); block=row['block'].strip(); district=row['district'].strip(); state=row['state'].strip()
            if not all([code,name,block,district,state]) or not code.isdigit() or len(code)!=11: raise ValueError('Required fields missing or UDISE code must be 11 digits')
            found=c.execute('SELECT id FROM schools WHERE udise_code=?',(code,)).fetchone()
            if found:
                c.execute('UPDATE schools SET name=?,block=?,district=?,state=?,data_origin=?,source_url=? WHERE id=?',(name,block,district,state,'Imported school master',row.get('source_url','')[:500],found['id'])); updated+=1
            else:
                sid='UDISE-'+code
                c.execute('INSERT INTO schools(id,name,block,district,state,udise_code,data_origin,management,source_url) VALUES(?,?,?,?,?,?,?,?,?)',(sid,name,block,district,state,code,'Imported school master',row.get('management','Unknown')[:80],row.get('source_url','')[:500])); added+=1
        except Exception as e:
            rejected+=1
            if len(errors)<50: errors.append({'row':rn,'reason':str(e)[:200]})
    m.log(c,u,'IMPORT','school_master',file.filename,f'{added} added; {updated} updated; {rejected} rejected; source={source_system}')
    c.commit(); c.close()
    return {'added':added,'updated':updated,'rejected':rejected,'errors':errors,'source_system':source_system,'note':'School directory metadata only. This does not establish school participation in ASER/PARAKH or provide learner outcomes.'}

@router.post('/api/import/authorised-roster')
async def import_authorised_roster(file:UploadFile=File(...), authorisation_reference:str=Form(''), u=Depends(get_user)):
    """Import minimal pseudonymous roster mapping after an authorised data-sharing approval."""
    from . import main as m
    if u['role'] not in ('block_officer','state_admin','admin'): raise HTTPException(403,'Roster imports are restricted')
    if not authorisation_reference.strip(): raise HTTPException(422,'Provide the data-sharing approval/reference ID')
    raw=await file.read()
    if len(raw)>10*1024*1024: raise HTTPException(413,'CSV exceeds 10 MB')
    try: reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    except UnicodeDecodeError: raise HTTPException(400,'CSV must be UTF-8')
    required={'learner_id','school_udise_code','grade','attendance_pct'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(422,{'missing':sorted(required-set(reader.fieldnames or []))})
    c=m.conn(); cols={r[1] for r in c.execute('PRAGMA table_info(learners)').fetchall()}
    if 'roster_authorisation_ref' not in cols: c.execute('ALTER TABLE learners ADD COLUMN roster_authorisation_ref TEXT')
    if 'data_origin' not in cols: c.execute("ALTER TABLE learners ADD COLUMN data_origin TEXT DEFAULT 'Synthetic demo'")
    added=updated=rejected=0; errors=[]
    for rn,row in enumerate(reader,2):
        try:
            lid=row['learner_id'].strip(); code=row['school_udise_code'].strip(); grade=int(row['grade']); attendance=float(row['attendance_pct'])
            if not lid or len(lid)>80 or grade not in range(1,9) or not 0<=attendance<=100: raise ValueError('Invalid learner ID, grade (1–8), or attendance (0–100)')
            school=c.execute('SELECT id FROM schools WHERE udise_code=?',(code,)).fetchone()
            if not school: raise ValueError('UDISE code not found; import/verify school master first')
            existing=c.execute('SELECT id,school_id,grade FROM learners WHERE id=?',(lid,)).fetchone()
            if existing and (existing['school_id']!=school['id'] or existing['grade']!=grade): raise ValueError('Existing learner mapping conflicts; resolve manually')
            if existing:
                c.execute('UPDATE learners SET attendance=?,roster_authorisation_ref=?,data_origin=? WHERE id=?',(attendance,authorisation_reference[:120],'Authorised pseudonymous roster',lid)); updated+=1
            else:
                c.execute("INSERT INTO learners(id,name,grade,school_id,gender,attendance,reading_level,numeracy_level,reading_score,numeracy_score,roster_authorisation_ref,data_origin) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(lid,'Learner '+lid,grade,school['id'],'Not collected',attendance,'Not assessed','Not assessed',None,None,authorisation_reference[:120],'Authorised pseudonymous roster')); added+=1
        except Exception as e:
            rejected+=1
            if len(errors)<50: errors.append({'row':rn,'learner_id':row.get('learner_id',''),'reason':str(e)[:200]})
    m.log(c,u,'IMPORT','authorised_roster',file.filename,f'{added} added; {updated} updated; {rejected} rejected; approval={authorisation_reference[:80]}')
    c.commit(); c.close()
    return {'added':added,'updated':updated,'rejected':rejected,'errors':errors,'authorisation_reference':authorisation_reference,'privacy':'Pseudonymous IDs only; names, Aadhaar, phone numbers and home addresses are not accepted or required.'}

@router.get('/api/validation/readiness')
def validation_readiness(u=Depends(get_user)):
    """Show whether the workspace has enough authorised longitudinal evidence to validate."""
    from . import main as m
    c=m.conn()
    batches=[dict(x) for x in c.execute("SELECT source_system,COUNT(*) batches,SUM(accepted_rows) accepted_rows,MAX(created_at) latest_import FROM assessment_import_batches GROUP BY source_system ORDER BY latest_import DESC").fetchall()]
    obs=c.execute('SELECT COUNT(*) n,COUNT(DISTINCT learner_id) learners,COUNT(DISTINCT school_id) schools,COUNT(DISTINCT assessed_on) dates,MIN(assessed_on) first_date,MAX(assessed_on) last_date FROM assessment_observations').fetchone()
    synthetic=c.execute("SELECT COUNT(*) FROM assessment_observations WHERE source_system LIKE '%demo%' OR source_system LIKE '%synthetic%' OR source_system LIKE '%legacy%'").fetchone()[0]
    authorised=c.execute("SELECT COUNT(*) FROM assessment_observations o JOIN assessment_import_batches b ON b.id=o.import_batch_id WHERE b.authorisation_reference IS NOT NULL AND b.authorisation_reference!=''").fetchone()[0]
    c.close()
    return {'observations':dict(obs),'import_batches':batches,'synthetic_or_legacy_observations':synthetic,'other_source_observations':authorised,'validation_gate':'not_ready' if authorised==0 else 'requires_provenance_review','requirements':['Approved data-sharing basis documented by the data controller','Pseudonymous learner IDs; no direct identifiers','At least two dated observations per learner-domain-competency pair, >=14 days apart','Multiple schools and multiple assessment periods','Comparable assessment scale and competency mapping across periods','Holdout schools and future assessment period untouched during model development'],'important':'Only batches with an entered authorisation reference are eligible for the ML validation query. A reference string is not proof: independently verify the approval document and source lineage before treating results as real-world validation.'}
