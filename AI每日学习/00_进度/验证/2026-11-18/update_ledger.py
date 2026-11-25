from pathlib import Path
import json,hashlib,re,fcntl,os,difflib
base=Path('/Users/alion/DemoProjects/ToDoList/AI每日学习');E=base/'00_进度/验证/2026-11-18';p=base/'00_进度/进度.md'
expected=json.loads((E/'inputs.json').read_text())['ledger_expected_sha256']
with p.open('rb') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 original=p.read_bytes();assert hashlib.sha256(original).hexdigest()==expected,'并发变更：停止更新台账'
 text=original.decode()
 assert not re.search(r'^\| 2026-11-18 \| 02_AndroidAI',text,re.M),'今天已登记，停止重复'
 backup=E/'进度.写前备份.md'
 if backup.exists():assert backup.read_bytes()==original,'备份不一致'
 else:
  with backup.open('xb') as f:f.write(original)
 last='| 2026-11-17 | 02_AndroidAI · 第 2 讲 | Prompt API 最小调用：能力门禁后的一次短文本生成 | 02_AndroidAI/2026-11-17-Prompt API最小调用：能力门禁后的一次短文本生成.md | 待填 |'
 row='| 2026-11-18 | 02_AndroidAI · 第 3 讲 | 端侧流式生成的 Compose 增量呈现（续地基 Streaming，Android 接入） | 02_AndroidAI/2026-11-18-端侧流式生成的Compose增量呈现.md | 待填 |'
 assert text.count(last)==1;text=text.replace(last,last+'\n'+row,1)
 plan='- [ ] Android × AI · 第 3 讲：端侧流式生成的 Compose 增量呈现（计划 2026-11-18；续地基 Streaming，聚焦 Android 接入，届时复核契约）'
 assert text.count(plan)==1
 text=text.replace(plan,'- [x] Android × AI · 第 3 讲：端侧流式生成的 Compose 增量呈现（2026-11-18 材料已产出；续地基 Streaming；官方增量/终帧契约已复核，Host 17 项通过，Android/Compose 编译与真机 NOT_EXECUTED；复述待填）',1)
 sources=json.loads((E/'sources.json').read_text())['sources'];used=[r for r in sources if r['used_in_material']]
 new=[];reused=[]
 for r in used:
  if r['dedup'].startswith('继续'):reused.append(r);continue
  label=('动态｜' if r['id'].startswith('N') else '岗位证据｜' if r['id']=='J03' else '岗位｜' if r['id']=='J04' else '工具证据｜' if r['id']=='T02' else '工具｜' if r['id']=='T01' else '教学参考｜')+r['title']
  new.append('| 2026-11-18 | '+label+' | '+r['url']+' |')
 end='| 2026-11-17 | 工具｜ML Kit GenAI Quickstart | https://github.com/googlesamples/mlkit/tree/master/android/genai |'
 assert text.count(end)==1;text=text.replace(end,end+'\n'+'\n'.join(new),1)
 note='> 2026-11-18 教学参考继续使用（非新动态）：'+'；'.join('['+r['id']+' '+r['title']+']('+r['url']+')' for r in reused)+'。全部引用的原来源日期、实读状态、canonical 去重与HTTP证据见 `验证/2026-11-18/sources.json`。本讲只续Android流式接入，不重讲SSE；摘要由主智能体验收后提交，本执行者 not_sent。\n\n'
 assert text.count('## 周总结')==1;text=text.replace('## 周总结',note+'## 周总结',1)
 tmp=E/'进度.待提交.tmp'
 with tmp.open('xb') as f:f.write(text.encode());f.flush();os.fsync(f.fileno())
 # 写前再次校验路径内容及锁的inode；不悄悄覆盖其他写入者的修改
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected and os.stat(p).st_ino==os.fstat(lock.fileno()).st_ino,'提交前并发变更，停止'
 os.replace(tmp,p)
 diff=''.join(difflib.unified_diff(original.decode().splitlines(True),text.splitlines(True),fromfile='进度.写前备份.md',tofile='进度.md'))
 (E/'ledger.diff').write_text(diff)
 print(diff)
 print('台账SHA256',hashlib.sha256(p.read_bytes()).hexdigest(),'新增链接',len(new),'继续使用',len(reused))
