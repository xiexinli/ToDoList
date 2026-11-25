from pathlib import Path
import json,re,hashlib,datetime,urllib.parse
base=Path('/Users/alion/DemoProjects/ToDoList/AI每日学习');E=base/'00_进度/验证/2026-11-18'
ledger=(base/'00_进度/进度.md').read_text()
expected=json.loads((E/'inputs.json').read_text())['ledger_expected_sha256']
assert hashlib.sha256((base/'00_进度/进度.md').read_bytes()).hexdigest()==expected,'台账并发变化，停止写入'
rows=[]
for n in ['sources_initial.json','sources_more.json','sources_final.json','sources_compose.json','sources_versioned.json']:
 rows+=json.loads((E/n).read_text())
labels={
'S01':'GenerativeModel流式签名、单候选、取消与close','S02':'StreamingCallback实际两个方法','S03':'响应候选与公开字段','S04':'候选文本与结束原因语义','S05':'Prompt接入指南：明确 += 追加流值','S06':'GenAI最上层前台要求','S07':'genai-prompt beta4 POM','S08':'Compose不可变状态与生命周期收集','S09':'viewModelScope生命周期','S10':'lifecycle-viewmodel-ktx 2.8.7 POM','S11':'lifecycle-runtime-compose 2.8.7 POM','S12':'material3 1.3.0 POM','S13':'FinishReason整数常量','S14':'Builder请求构造与属性','S15':'TextPart构造器','S16':'Generation.getClient','S17':'协程1.7.3 Timeout源码','S18':'Compose包与LocalLifecycleOwner','S19':'协程1.7.3 Mutex源码','S20':'当前在线生命周期收集函数签名','S21':'lifecycle-runtime-compose-android 2.8.7版本源码','N01':'动态：AI Studio全栈Android','J03':'岗位正文：腾讯小程序智能体详情API','J04':'岗位：腾讯小程序智能体网页','T01':'工具：android/compose-samples','T02':'工具证据：Jetchat README'}
def canonical(url):
 p=urllib.parse.urlsplit(url);return p.netloc.lower()+p.path.rstrip('/')+('?' + urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(p.query))) if p.query else '')
old={canonical(u) for u in re.findall(r'https?://[^\s|)；]+',ledger)}
used=[];table=['| ID | 实读来源 | 原日期/版本与去重 |','|---|---|---|']
for r in rows:
 sid=r['id'];r['used_in_material']=sid in labels
 if sid not in labels:
  r['read_state']='READ_DISCOVERY_CANDIDATES';continue
 assert r['http']=='200' and r['curl_exit']==0,(sid,r)
 r['title']=labels[sid];r['canonical']=canonical(r['url'])
 r['dedup']='继续使用，非新动态' if r['canonical'] in old else ('首次动态/岗位/工具收录' if sid[0] in 'NJT' else '首次教学参考')
 r['read_state']='READ_VERSIONED_SOURCE' if sid=='S21' else ('READ_JS_SHELL;正文另见J03' if sid=='J04' else 'READ_BODY_OR_SOURCE')
 date=(r.get('datePublished') or [None])[0]
 if sid in ['J03','J04']:date='更新2026-11-11；原发布日期未提供'
 if not date:date=re.sub(r'Last updated | UTC\..*','',(r.get('last_updated') or [''])[0]) or r.get('source_date') or '版本文件/源码未给原发布日期'
 r['source_date']=date
 used.append(r)
 table.append('| '+sid+' | ['+labels[sid]+']('+r['url']+') | '+date+'；'+r['dedup']+' |')
for sid in ['N01','J03','J04','T01','T02']:
 assert next(r for r in used if r['id']==sid)['canonical'] not in old,'动态重复：'+sid
text=(E/'material.template.md').read_text()
for key,value in {'@@SOURCE_TABLE@@':'\n'.join(table),'@@PYTHON@@':(E/'stream_contract.py').read_text().rstrip(),'@@KOTLIN@@':(E/'NanoStreamScreen.kt').read_text().rstrip(),'@@FIXTURE_LOG@@':(E/'fixture-run.log').read_text().rstrip()}.items():text=text.replace(key,value)
assert '@@' not in text
for u in re.findall(r'\]\((https?://[^)]+)\)',text):assert u in {r['url'] for r in used},u
out=base/'02_AndroidAI/2026-11-18-端侧流式生成的Compose增量呈现.md'
assert not list((base/'01_地基').glob('2026-11-18*')) and not list((base/'02_AndroidAI').glob('2026-11-18*')),'今日已出现产物，停止覆盖'
with out.open('x',encoding='utf-8') as f:f.write(text)
(E/'sources.json').write_text(json.dumps({'observed_date':'2026-11-18','ledger_before_sha256':expected,'sources':rows,'used_count':len(used),'new_dynamic_count':1,'job_count':1,'tool_count':1},ensure_ascii=False,indent=2))
print('已写主文件',out,'sha256',hashlib.sha256(out.read_bytes()).hexdigest(),'来源',len(used))
