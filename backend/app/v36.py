"""NIPUNSetu v3.6: defensible local-to-public benchmark comparison.

Direct comparisons are only emitted when indicator, unit, grade, population, assessment mode,
instrument and sampling design match exactly. Otherwise public values are contextual references.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
import csv, io, datetime

router = APIRouter()

def user_dep(authorization: str | None = Header(None)):
    from . import main as m
    return m.current_user(authorization)

DDL = '''
CREATE TABLE IF NOT EXISTS local_benchmark_observations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 observation_id TEXT NOT NULL UNIQUE,
 school_id TEXT NOT NULL,
 school_name TEXT NOT NULL,
 block TEXT NOT NULL,
 district TEXT NOT NULL,
 state TEXT NOT NULL,
 grade INTEGER NOT NULL,
 domain TEXT NOT NULL,
 indicator TEXT NOT NULL,
 value REAL NOT NULL,
 unit TEXT NOT NULL,
 population TEXT NOT NULL,
 assessment_mode TEXT NOT NULL,
 assessment_instrument TEXT NOT NULL,
 sampling_design TEXT NOT NULL,
 assessed_on TEXT NOT NULL,
 sample_size INTEGER NOT NULL,
 source_label TEXT NOT NULL,
 source_reference TEXT,
 imported_by TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_local_benchmark_match ON local_benchmark_observations(indicator,unit,grade,population,assessment_mode,assessed_on);
'''

def init_store():
    from . import main as m
    c=m.conn(); c.executescript(DDL)
    c.executescript('''CREATE TABLE IF NOT EXISTS aligned_public_references (
      id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL, geography_name TEXT NOT NULL,
      year INTEGER NOT NULL, grade INTEGER NOT NULL, domain TEXT NOT NULL, indicator TEXT NOT NULL,
      value REAL NOT NULL, unit TEXT NOT NULL, population TEXT NOT NULL, assessment_mode TEXT NOT NULL,
      assessment_instrument TEXT NOT NULL, sampling_design TEXT NOT NULL, source_url TEXT NOT NULL, source_page TEXT,
      imported_by TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(source_id,geography_name,year,grade,indicator,unit,population,assessment_mode,assessment_instrument));
      CREATE INDEX IF NOT EXISTS idx_aligned_reference_match ON aligned_public_references(indicator,unit,grade,population,assessment_mode,assessment_instrument);''')
    cols={r[1] for r in c.execute('PRAGMA table_info(local_benchmark_observations)').fetchall()}
    if 'sampling_design' not in cols: c.execute("ALTER TABLE local_benchmark_observations ADD COLUMN sampling_design TEXT NOT NULL DEFAULT 'unspecified'")
    cols={r[1] for r in c.execute('PRAGMA table_info(aligned_public_references)').fetchall()}
    if 'sampling_design' not in cols: c.execute("ALTER TABLE aligned_public_references ADD COLUMN sampling_design TEXT NOT NULL DEFAULT 'unspecified'")
    c.commit(); c.close()

@router.get('/api/comparison/template')
def comparison_template(u=Depends(user_dep)):
    cols=['observation_id','school_id','grade','domain','indicator','value','unit','population','assessment_mode','assessment_instrument','sampling_design','assessed_on','sample_size','source_label','source_reference']
    out=io.StringIO(); w=csv.writer(out); w.writerow(cols)
    w.writerow(['OBS-001','SCH001',3,'reading','read_std2_text_govt',24.0,'percent_children','government_school_children_std3_rural','one_on_one_oral','ASER-aligned task protocol; verify exact tool and administration','school_census_or_declared_sample_design','2026-09-15',30,'Authorised school assessment export','approval-reference-REPLACE'])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=nipunsetu_comparison_observations_template.csv'})

@router.post('/api/comparison/import-local')
async def import_local_observations(file: UploadFile=File(...), u=Depends(user_dep)):
    from . import main as m
    if u['role'] not in ('block_officer','state_admin','admin'):
        raise HTTPException(403,'Local benchmark imports are restricted to block/state administrators')
    if not (file.filename or '').lower().endswith('.csv'):
        raise HTTPException(400,'Upload a CSV file')
    raw=await file.read()
    if len(raw)>5*1024*1024: raise HTTPException(413,'CSV exceeds 5 MB')
    try: reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    except UnicodeDecodeError: raise HTTPException(400,'CSV must be UTF-8')
    required={'observation_id','school_id','grade','domain','indicator','value','unit','population','assessment_mode','assessment_instrument','sampling_design','assessed_on','sample_size','source_label','source_reference'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(422,{'missing':sorted(required-set(reader.fieldnames or []))})
    c=m.conn(); added=duplicates=rejected=0; errors=[]
    for rn,row in enumerate(reader,2):
        try:
            oid=row['observation_id'].strip(); sid=row['school_id'].strip(); school=c.execute('SELECT * FROM schools WHERE id=?',(sid,)).fetchone()
            if not oid or not school: raise ValueError('observation_id and an existing school_id are required')
            grade=int(row['grade']); value=float(row['value']); n=int(row['sample_size']); day=datetime.date.fromisoformat(row['assessed_on'].strip())
            if not 1<=grade<=8 or not 0<=value<=100 or n<1: raise ValueError('grade must be 1–8, value 0–100, sample_size >= 1')
            domain=row['domain'].strip().lower()
            if domain not in ('reading','numeracy'): raise ValueError('domain must be reading or numeracy')
            for key in ('indicator','unit','population','assessment_mode','assessment_instrument','sampling_design','source_label','source_reference'):
                if not row[key].strip(): raise ValueError(f'{key} is required')
            c.execute('''INSERT OR IGNORE INTO local_benchmark_observations
            (observation_id,school_id,school_name,block,district,state,grade,domain,indicator,value,unit,population,assessment_mode,assessment_instrument,sampling_design,assessed_on,sample_size,source_label,source_reference,imported_by)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (oid,sid,school['name'],school['block'],school['district'],school['state'],grade,domain,row['indicator'].strip(),value,row['unit'].strip(),row['population'].strip(),row['assessment_mode'].strip(),row['assessment_instrument'].strip(),row['sampling_design'].strip(),day.isoformat(),n,row['source_label'].strip(),(row.get('source_reference') or '')[:300],u['id']))
            if c.execute('SELECT changes()').fetchone()[0]: added+=1
            else: duplicates+=1
        except Exception as e:
            rejected+=1
            if len(errors)<50: errors.append({'row':rn,'reason':str(e)[:220]})
    m.log(c,u,'IMPORT','local_benchmark_observations',file.filename,f'{added} added; {duplicates} duplicates; {rejected} rejected')
    c.commit(); c.close()
    return {'added':added,'duplicates':duplicates,'rejected':rejected,'errors':errors,'note':'Imported school observations are compared directly only when measurement metadata exactly matches a published benchmark.'}

@router.get('/api/comparison/reference-template')
def comparison_reference_template(u=Depends(user_dep)):
    cols=['source_id','geography_name','year','grade','domain','indicator','value','unit','population','assessment_mode','assessment_instrument','sampling_design','source_url','source_page']
    out=io.StringIO(); w=csv.writer(out); w.writerow(cols)
    w.writerow(['STATE_ASSESSMENT','Example District',2026,3,'reading','read_std2_text_govt',26.0,'percent_children','government_school_children_std3_rural','one_on_one_oral','Exact validated task and administration protocol','two_stage_household_sample','https://asercentre.org/aser-2024/','Report page / table'])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=nipunsetu_aligned_public_reference_template.csv'})

@router.post('/api/comparison/import-reference')
async def import_aligned_reference(file: UploadFile=File(...), u=Depends(user_dep)):
    from . import main as m
    if u['role'] not in ('block_officer','state_admin','admin'): raise HTTPException(403,'Reference imports are restricted')
    if not (file.filename or '').lower().endswith('.csv'): raise HTTPException(400,'Upload a CSV file')
    raw=await file.read()
    if len(raw)>5*1024*1024: raise HTTPException(413,'CSV exceeds 5 MB')
    try: reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    except UnicodeDecodeError: raise HTTPException(400,'CSV must be UTF-8')
    required={'source_id','geography_name','year','grade','domain','indicator','value','unit','population','assessment_mode','assessment_instrument','sampling_design','source_url'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(422,{'missing':sorted(required-set(reader.fieldnames or []))})
    c=m.conn(); added=duplicates=rejected=0; errors=[]
    allowed_hosts=('asercentre.org','parakh.ncert.gov.in','dashboard.parakh.ncert.gov.in','udiseplus.gov.in','data.gov.in','gov.in')
    for rn,row in enumerate(reader,2):
        try:
            year=int(row['year']); grade=int(row['grade']); value=float(row['value']); domain=row['domain'].strip().lower(); url=row['source_url'].strip()
            if not 2000<=year<=datetime.date.today().year or not 1<=grade<=8 or not 0<=value<=100: raise ValueError('Invalid year, grade or value')
            if domain not in ('reading','numeracy'): raise ValueError('domain must be reading or numeracy')
            if row['source_id'].strip() not in ('ASER2024','PARAKH2024','STATE_SCERT','SEAS2023','FLS2022','UDISEPLUS'): raise ValueError('source_id must identify a recognised education source')
            if not url.startswith('https://') or not any(h in url.lower() for h in allowed_hosts): raise ValueError('source_url must be an official education/government HTTPS source')
            for k in ('source_id','geography_name','indicator','unit','population','assessment_mode','assessment_instrument','sampling_design'):
                if not row[k].strip(): raise ValueError(f'{k} is required')
            c.execute('INSERT OR IGNORE INTO aligned_public_references(source_id,geography_name,year,grade,domain,indicator,value,unit,population,assessment_mode,assessment_instrument,sampling_design,source_url,source_page,imported_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (row['source_id'].strip(),row['geography_name'].strip(),year,grade,domain,row['indicator'].strip(),value,row['unit'].strip(),row['population'].strip(),row['assessment_mode'].strip(),row['assessment_instrument'].strip(),row['sampling_design'].strip(),url,(row.get('source_page') or '')[:200],u['id']))
            if c.execute('SELECT changes()').fetchone()[0]: added+=1
            else: duplicates+=1
        except Exception as e:
            rejected+=1
            if len(errors)<50: errors.append({'row':rn,'reason':str(e)[:220]})
    m.log(c,u,'IMPORT','aligned_public_reference',file.filename,f'{added} added; {duplicates} duplicates; {rejected} rejected')
    c.commit(); c.close()
    return {'added':added,'duplicates':duplicates,'rejected':rejected,'errors':errors,'note':'Direct comparison requires exact match across grade, domain, indicator, unit, population, assessment mode, instrument and sampling design.'}

@router.get('/api/comparison/overview')
def comparison_overview(school_id: str | None=Query(None), grade: int=Query(3,ge=1,le=8), domain: str=Query('reading'), u=Depends(user_dep)):
    from . import main as m
    if domain not in ('reading','numeracy'): raise HTTPException(422,'domain must be reading or numeracy')
    c=m.conn()
    schools=c.execute('SELECT id,name,block,district,state FROM schools ORDER BY name').fetchall()
    if u['role']=='teacher': schools=[s for s in schools if s['id']==u['school_id']]
    if school_id and not any(s['id']==school_id for s in schools): c.close(); raise HTTPException(403,'School outside your access scope')
    chosen=next((s for s in schools if s['id']==school_id), schools[0] if schools else None)
    if not chosen: c.close(); return {'school':None,'grade':grade,'domain':domain,'local':None,'direct_comparisons':[],'contextual_references':[],'rules':[]}
    local=c.execute('''SELECT COUNT(*) learners,ROUND(AVG(CASE WHEN ?='reading' THEN reading_score ELSE numeracy_score END),1) mean_score
      FROM learners WHERE school_id=? AND grade=?''',(domain,chosen['id'],grade)).fetchone()
    observations=[dict(x) for x in c.execute('''SELECT * FROM local_benchmark_observations WHERE school_id=? AND grade=? AND domain=? ORDER BY assessed_on DESC''',(chosen['id'],grade,domain)).fetchall()]
    benchmarks=[dict(x) for x in c.execute('SELECT * FROM public_benchmarks WHERE grade=? AND domain=? ORDER BY year DESC',(grade,domain)).fetchall()]
    aligned=[dict(x) for x in c.execute('SELECT * FROM aligned_public_references WHERE grade=? AND domain=? ORDER BY year DESC',(grade,domain)).fetchall()]
    direct=[]; contextual=[]
    for ref in aligned:
        match=next((o for o in observations if all(o[k]==ref[k] for k in ('indicator','unit','population','assessment_mode','assessment_instrument','sampling_design'))),None)
        if match:
            direct.append({'reference':ref,'local_observation':match,'difference':round(match['value']-ref['value'],2),'difference_unit':'percentage_points' if ref['unit'].startswith('percent') else ref['unit'],'interpretation':'Descriptive difference only; review sample size, sampling design and uncertainty before decisions.'})
        else:
            contextual.append({**ref,'reason':'No local observation with an exact matching measurement contract.'})
    for b in benchmarks:
        contextual.append({**b,'reason':'Published seed lacks a complete matching population, assessment mode and instrument contract. Context only; never subtract from local mean score.'})
    # Explicitly comparable benchmark pairs can be enabled only when the source row carries a declared protocol contract.
    return {'school':dict(chosen),'grade':grade,'domain':domain,'local':{'learners':local['learners'],'mean_score':local['mean_score'],'unit':'local_mean_score_0_100','data_origin':'learner records; demo/synthetic unless imported under an approved source workflow'},'local_observations':observations,'direct_comparisons':direct,'contextual_references':contextual[:30],
      'rules':['Local learner mean score (0–100) is not the same metric as the percentage of children reaching a task threshold (ASER).','PARAKH percentage-correct competency results are not automatically equivalent to a locally computed learner mean.','ASER is a rural household sample; PARAKH is a sampled school assessment. Coverage and administration differ.','No direct comparison is published unless indicator, unit, grade, population, assessment mode, instrument and sampling design are explicitly aligned.'],
      'status':'direct_only_on_exact_protocol_match' if direct else 'context_only_until_protocol_alignment','message':('Exact protocol-aligned descriptive comparisons are available. Review sample size and uncertainty before drawing conclusions.' if direct else 'Current public benchmarks are contextual references. Import source and local observations with exactly matching indicator, unit, population, assessment mode, instrument and sampling design to enable a direct descriptive comparison.')}
