"""NIPUNSetu v3.5 public benchmark registry and aggregate-data ingestion.

Seeded figures are transcribed from official ASER 2024 / PARAKH 2024 publications.
They remain population-level benchmarks and are never expanded into learner records.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header
from fastapi.responses import StreamingResponse
import csv, io, json, secrets, datetime

router = APIRouter()

def user_dep(authorization: str | None = Header(None)):
    from . import main as m
    return m.current_user(authorization)

SOURCES = [
 {"id":"ASER2024","name":"ASER 2024","publisher":"ASER Centre / Pratham","kind":"Household survey; rural India","coverage":"National and state estimates; selected district estimates available separately","url":"https://asercentre.org/aser-2024/","data_access":"Published report and state pages; research microdata by request","boundary":"ASER is household-based, not a school census. Published aggregate estimates cannot be assigned to individual learners or individual schools."},
 {"id":"PARAKH2024","name":"PARAKH Rashtriya Sarvekshan 2024","publisher":"PARAKH, NCERT / Ministry of Education","kind":"Large-scale sampled assessment","coverage":"Grades 3, 6 and 9; 36 States/UTs and 781 districts","url":"https://parakh.ncert.gov.in/prs-reports-2024/","data_access":"National/state/district reports and dashboard","boundary":"Sampled assessment results are aggregate/system-level evidence, not a roster of every child or school."},
 {"id":"UDISEPLUS","name":"UDISE+","publisher":"Department of School Education & Literacy, Ministry of Education","kind":"Administrative school data system","coverage":"School directory and school-level administrative indicators subject to access and publication rules","url":"https://www.udiseplus.gov.in/","data_access":"Published reports, OGD catalog and authorised portal exports","boundary":"School master data does not itself contain learner-level FLN outcomes. Respect portal permissions and source-year definitions."},
 {"id":"DIKSHA","name":"DIKSHA","publisher":"Ministry of Education","kind":"Digital learning resources","coverage":"Curriculum-linked resources across languages and grades","url":"https://diksha.gov.in/","data_access":"Public portal discovery; integrations subject to API and platform terms","boundary":"Resource links are discovery references, not proof that a resource was completed or improved learning."},
]

# Verified published aggregate indicators. Values are percentages of children/answers as
# explicitly defined by the cited source; they are not scores on NIPUNSetu's 0-100 test scale.
SEED = [
 # ASER 2024 national rural, all school types
 ("ASER2024","India (rural)","national",2024,3,"reading","read_std2_text","27.1","percent_children","All children in Std III able to read Std II level text; rural India; government+private weighted estimate.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2024,3,"reading","read_std2_text_govt","23.4","percent_children","Std III children in government schools able to read Std II level text.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2024,3,"numeracy","subtraction_govt","27.6","percent_children","Std III children in government schools able to solve at least a subtraction problem.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2024,3,"numeracy","subtraction_all","33.7","percent_children","Std III children across government and private schools able to solve at least a subtraction problem.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2024,5,"reading","read_std2_text_govt","44.8","percent_children","Std V government-school children able to read Std II level text.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2024,5,"numeracy","division_all","30.7","percent_children","Std V children able to solve a division problem; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","Uttar Pradesh (rural)","state",2024,3,"reading","read_std2_text_govt","27.9","percent_children","Std III government-school children able to read Std II level text.","https://asercentre.org/aser-2024/","Uttar Pradesh state report"),
 # ASER 2024 trend series (rural India, all school types unless stated)
 ("ASER2024","India (rural)","national",2018,3,"reading","read_std2_text_all",27.3,"percent_children","Std III children able to read Std II level text; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2022,3,"reading","read_std2_text_all",20.5,"percent_children","Std III children able to read Std II level text; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2018,3,"reading","read_std2_text_govt",20.9,"percent_children","Std III government-school children able to read Std II level text.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2022,3,"reading","read_std2_text_govt",16.3,"percent_children","Std III government-school children able to read Std II level text.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2018,3,"numeracy","subtraction_govt",20.9,"percent_children","Std III government-school children able to solve at least subtraction.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2022,3,"numeracy","subtraction_govt",20.2,"percent_children","Std III government-school children able to solve at least subtraction.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2018,3,"numeracy","subtraction_all",28.2,"percent_children","Std III children able to solve at least subtraction; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2022,3,"numeracy","subtraction_all",25.9,"percent_children","Std III children able to solve at least subtraction; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2018,5,"reading","read_std2_text_govt",44.2,"percent_children","Std V government-school children able to read Std II level text.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2022,5,"reading","read_std2_text_govt",38.5,"percent_children","Std V government-school children able to read Std II level text.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2018,5,"numeracy","division_all",27.9,"percent_children","Std V children able to solve division; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 ("ASER2024","India (rural)","national",2022,5,"numeracy","division_all",25.6,"percent_children","Std V children able to solve division; all school types.","https://asercentre.org/wp-content/uploads/2022/12/ASER-2024-National-findings.pdf","47"),
 # PARAKH 2024 survey coverage facts (not outcome scores)
 ("PARAKH2024","India","national",2024,None,"other","children_assessed",2115022,"children","Children assessed across Grades 3, 6 and 9.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, overview"),
 ("PARAKH2024","India","national",2024,None,"other","schools_participated",74229,"schools","Unique participating schools across 781 districts and 36 States/UTs.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, overview"),
 ("PARAKH2024","India","national",2024,None,"other","districts_covered",781,"districts","Districts covered by the survey.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, overview"),
 ("PARAKH2024","India","national",2024,None,"other","teachers_school_leaders_responded",270424,"people","Teachers and school leaders responding through questionnaires.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, overview"),
 # PARAKH 2024 Grade 3 competency benchmarks (national % correct)
 ("PARAKH2024","India","national",2024,3,"reading","C-9.7","67","percent_correct","Grade 3 language competency: vocabulary for day-to-day interactions and inferring new word meanings.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"reading","C-10.5","60","percent_correct","Grade 3 language competency: reads and comprehends short stories.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"reading","C-10.7","61","percent_correct","Grade 3 language competency: comprehends short news items, instructions, recipes and publicity material.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.1","68","percent_correct","Sorts objects into groups and sub-groups based on more than one property.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.2","69","percent_correct","Identifies and extends simple patterns.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.4","55","percent_correct","Arranges numbers up to 99 in ascending and descending order.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.5","61","percent_correct","Represents quantities up to 99 using numerals and decimal place value.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.6","58","percent_correct","Adds and subtracts two-digit numbers using flexible strategies.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.7","54","percent_correct","Recognises multiplication as repeated addition and division as equal sharing.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.8","50","percent_correct","Recognises and classifies basic geometric shapes and spatial relations.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.9","62","percent_correct","Selects tools and units for simple measurement.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.10","61","percent_correct","Measures time in minutes, hours, days, weeks and months.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.11","50","percent_correct","Performs simple transactions using money up to INR 100.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.12","55","percent_correct","Uses vocabulary to express concepts related to quantities, shapes, space and measurement.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
 ("PARAKH2024","India","national",2024,3,"numeracy","C-8.13","55","percent_correct","Formulates and solves simple mathematical problems.","https://parakh.ncert.gov.in/sites/default/files/2025-07/REPORT_India_IND.pdf","National report, competency-wise performance Grade 3"),
]


def init_store():
    from . import main as m
    c=m.conn()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS public_benchmarks(
      id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL, geography_name TEXT NOT NULL,
      geography_level TEXT NOT NULL, year INTEGER NOT NULL, grade INTEGER, domain TEXT NOT NULL,
      indicator TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL, definition TEXT NOT NULL,
      source_url TEXT NOT NULL, source_page TEXT, imported_by TEXT DEFAULT 'official-seed',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(source_id,geography_name,year,grade,domain,indicator,unit));
    CREATE INDEX IF NOT EXISTS idx_public_benchmark ON public_benchmarks(source_id,year,geography_level,grade,domain);
    ''')
    for r in SEED:
        exists=c.execute('SELECT 1 FROM public_benchmarks WHERE source_id=? AND geography_name=? AND year=? AND grade IS ? AND domain=? AND indicator=? AND unit=? LIMIT 1',(r[0],r[1],r[3],r[4],r[5],r[6],r[8])).fetchone()
        if not exists:
            c.execute('INSERT INTO public_benchmarks(source_id,geography_name,geography_level,year,grade,domain,indicator,value,unit,definition,source_url,source_page) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(r[0],r[1],r[2],r[3],r[4],r[5],r[6],float(r[7]),r[8],r[9],r[10],r[11]))
    c.commit(); c.close()

@router.get('/api/public-data/overview')
def public_data_overview(u=Depends(user_dep)):
    from . import main as m
    c=m.conn(); rows=[dict(x) for x in c.execute('SELECT * FROM public_benchmarks ORDER BY source_id,grade,domain,indicator').fetchall()]; c.close()
    counts={s['id']:sum(1 for x in rows if x['source_id']==s['id']) for s in SOURCES}
    return {'sources':SOURCES,'source_counts':counts,'benchmarks':rows,'total_benchmarks':len(rows),
      'coverage_note':'Seeded values are published aggregates only. ASER is rural household-survey evidence; PARAKH is sampled system-level evidence; neither is a learner roster. UDISE+ school data is a separate administrative source.',
      'integration_status':{'ASER2024':'Official national findings seeded; state/district aggregate imports supported via CSV. Research microdata requires request to ASER Centre.','PARAKH2024':'Official national competency benchmarks seeded; state/district reports linked; aggregate CSV import supported.','UDISEPLUS':'School master CSV adapter already available; official portal exports require valid access.','DIKSHA':'Official discovery portal linked; no private API or completion telemetry assumed.'}}

@router.get('/api/public-data/template')
def public_data_template(u=Depends(user_dep)):
    cols=['source_id','geography_name','geography_level','year','grade','domain','indicator','value','unit','definition','source_url','source_page']
    out=io.StringIO(); w=csv.writer(out); w.writerow(cols)
    w.writerow(['ASER2024','Uttar Pradesh (rural)','state',2024,3,'reading','read_std2_text_govt',27.9,'percent_children','Std III govt school children reading Std II text','https://asercentre.org/aser-2024/','UP state report'])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=nipunsetu_public_aggregate_template.csv'})

@router.post('/api/public-data/import-aggregate')
async def import_public_aggregate(file:UploadFile=File(...),u=Depends(user_dep)):
    from . import main as m
    if u['role'] not in ('block_officer','state_admin','admin'): raise HTTPException(403,'Aggregate benchmark imports are restricted')
    if not (file.filename or '').lower().endswith('.csv'): raise HTTPException(400,'Upload a CSV file')
    raw=await file.read()
    if len(raw)>5*1024*1024: raise HTTPException(413,'CSV exceeds 5 MB')
    try: reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    except UnicodeDecodeError: raise HTTPException(400,'CSV must be UTF-8')
    required={'source_id','geography_name','geography_level','year','grade','domain','indicator','value','unit','definition','source_url'}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)): raise HTTPException(422,{'missing':sorted(required-set(reader.fieldnames or []))})
    allowed={s['id'] for s in SOURCES if s['id'] in ('ASER2024','PARAKH2024','UDISEPLUS')}
    added=duplicates=rejected=0; errors=[]; c=m.conn()
    for rn,row in enumerate(reader,2):
        try:
            sid=row['source_id'].strip(); geo=row['geography_name'].strip(); level=row['geography_level'].strip().lower(); year=int(row['year']); grade=int(row['grade']) if row.get('grade','').strip() else None; domain=row['domain'].strip().lower(); indicator=row['indicator'].strip(); value=float(row['value']); unit=row['unit'].strip(); definition=row['definition'].strip(); url=row['source_url'].strip()
            if sid not in allowed: raise ValueError('source_id must be ASER2024, PARAKH2024 or UDISEPLUS')
            if level not in ('national','state','district','block','school'): raise ValueError('Invalid geography_level')
            if not geo or not indicator or not definition: raise ValueError('geography_name, indicator and definition are required')
            if not 2000<=year<=datetime.date.today().year or (grade is not None and not 1<=grade<=12): raise ValueError('Invalid year or grade')
            if domain not in ('reading','numeracy','language','mathematics','enrolment','attendance','infrastructure','other'): raise ValueError('Invalid domain')
            if not 0<=value<=100000000: raise ValueError('Value outside permitted range')
            if not url.startswith('https://') or not any(host in url.lower() for host in ('asercentre.org','parakh.ncert.gov.in','dashboard.parakh.ncert.gov.in','udiseplus.gov.in','data.gov.in')): raise ValueError('source_url must be an official ASER/PARAKH/UDISE+/data.gov.in HTTPS source')
            c.execute('''INSERT OR IGNORE INTO public_benchmarks(source_id,geography_name,geography_level,year,grade,domain,indicator,value,unit,definition,source_url,source_page,imported_by)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sid,geo,level,year,grade,domain,indicator,value,unit,definition,url,row.get('source_page','')[:200],u['id']))
            if c.execute('SELECT changes()').fetchone()[0]: added+=1
            else: duplicates+=1
        except Exception as e:
            rejected+=1
            if len(errors)<50: errors.append({'row':rn,'reason':str(e)[:240]})
    m.log(c,u,'IMPORT','public_aggregate',file.filename,f'{added} added; {duplicates} duplicates; {rejected} rejected')
    c.commit(); c.close()
    return {'added':added,'duplicates':duplicates,'rejected':rejected,'errors':errors,'note':'Aggregate benchmark rows only. They are not joined to individual learners or used as learner-level training labels.'}
