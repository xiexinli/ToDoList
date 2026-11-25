"""唯一写者：写前备份/hash校验，保留全部旧行与用户复述；不操作旧课/规则。"""
from pathlib import Path
import hashlib, json, re, difflib, fcntl, os
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
b=Path('/Users/alion/DemoProjects/ToDoList/AI每日学习'); v=b/'00_进度/验证/2026-11-19'
p=b/'00_进度/进度.md'
f=b/'02_AndroidAI/2026-11-19-端侧生成的性能测量：首字时延与完整耗时.md'
def sha(data): return hashlib.sha256(data).hexdigest()
def canon(u):
 s=urlsplit(u); return urlunsplit(('https',s.netloc.lower(),s.path.rstrip('/'),urlencode(sorted(parse_qsl(s.query))),''))
inputs=json.loads((v/'inputs.json').read_text()); expected=next(x['sha256'] for x in inputs if x['path']==str(p))
with p.open('rb') as locked:
 fcntl.flock(locked.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 raw=locked.read(); assert sha(raw)==expected, '台账并发变更，停止而不覆盖'
 old=raw.decode('utf-8'); assert '| 2026-11-19 |' not in old, '今日已登记，停止重写'
 assert f.exists()
 backup=v/'ledger.before.md'; assert not backup.exists(), '备份已存在，需人工核验'
 backup.write_bytes(raw)
 row='| 2026-11-19 | 02_AndroidAI · 第 4 讲 | 端侧生成的性能测量：首字时延与完整耗时 | 02_AndroidAI/2026-11-19-端侧生成的性能测量：首字时延与完整耗时.md | 待填 |\n'
 anchor='\n\n> 欠产与补写记录：'; assert old.count(anchor)==1
 new=old.replace(anchor,row+anchor,1)
 plan='- [x] Android × AI · 第 4 讲：端侧生成的性能测量：首字时延与完整耗时（2026-11-19 材料已产出；Host合成时序26项通过，不是Nano性能；Android编译/真机NOT_EXECUTED；复述待填）\n'
 new=new.replace('\n## 动态链接去重表','\n'+plan+'\n## 动态链接去重表',1)
 sources=json.loads((v/'sources.json').read_text())
 referenced={canon(u) for u in re.findall(r'https?://[^\s|)>]+',f.read_text())}
 assert referenced=={s['canonical'] for s in sources}, '材料外链与来源表不一致'
 old_urls={canon(u) for u in re.findall(r'https?://[^\s|)>]+',old)}
 added=[]; continued=[]
 for s in sources:
  assert s['curl_exit']==0 and s['http']=='200'
  s['reuse']=s['canonical'] in old_urls
  matches=[line for line in old.splitlines() if line.startswith('| 2026-') and any(canon(u)==s['canonical'] for u in re.findall(r'https?://[^\s|)>]+',line))]
  s['first_seen']=matches[0].split('|')[1].strip() if matches else '2026-11-19'
  s['date_kind']='updated' if s['id'].startswith('S') and s['source_dates'] or s['id']=='T01' else 'published' if s['id']=='N01' else 'version_only_or_not_provided'
  if s['id'].startswith('J'): s['source_dates']=['2026-10-26']; s['date_kind']='job_updated; published_not_provided'
  if s['reuse']: continued.append(s)
  else: added.append('| 2026-11-19 | '+s['title']+' | '+s['url']+' |\n')
 anchor='\n> 2026-11-17 教学参考'; assert new.count(anchor)==1
 new=new.replace(anchor,''.join(added)+anchor,1)
 footer='\n> 2026-11-19 教学参考继续使用（非新动态）：'+'；'.join('['+s['id']+' '+s['title']+']('+s['url']+')' for s in continued)+'。当天全部12条引用的日期/正文定位/canonical去重/HTTP证据见 `验证/2026-11-19/sources.json`。本课仅测量边界；26项Host测试为合成时序断言，非Nano性能。Android编译/真机NOT_EXECUTED；本执行者摘要not_sent，由主智能体独立验收后处理。\n'
 new=new.replace('\n## 周总结',footer+'\n## 周总结',1)
 # 最后再次从路径校验，防止持锁期间另一个不合作写者替换文件。
 assert sha(p.read_bytes())==expected, '写前二次hash不一致，停止'
 staged=v/'ledger.staged.md'; staged.write_text(new,encoding='utf-8'); os.chmod(staged,p.stat().st_mode & 0o777)
 os.replace(staged,p)
 assert p.read_text()==new
 (v/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
 (v/'ledger.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='ledger.before.md',tofile='进度.md')),encoding='utf-8')
 (v/'ledger-change.json').write_text(json.dumps({'before':expected,'after':sha(p.read_bytes()),'backup':str(backup),'completed_rows_added':1,'plan_checked_added':1,'new_canonical_rows':len(added),'continued_references':len(continued),'all_old_lines_preserved':all(line in new for line in old.splitlines()),'write_guard':'nonblocking advisory flock + before/just-before-replace SHA256','feishu':'not_sent'},ensure_ascii=False,indent=2)+'\n')
 print((v/'ledger.diff').read_text())
 print((v/'ledger-change.json').read_text())
