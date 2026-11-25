"""只保存来源定位摘录/哈希/HTTP/日期，不保留网页全集，不读取凭据。"""
import subprocess, re, json, hashlib, datetime
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
BASE=Path('/Users/alion/DemoProjects/ToDoList/AI每日学习')
OUT=BASE/'00_进度/验证/2026-11-19'
class Text(HTMLParser):
 def __init__(self): super().__init__(); self.out=[]; self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'): self.skip+=1
 def handle_endtag(self,t):
  if t in ('script','style'): self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip(): self.out.append(d.strip())
def canonical(u):
 p=urlsplit(u); return urlunsplit(('https',p.netloc.lower(),p.path.rstrip('/'),urlencode(sorted(parse_qsl(p.query))),''))
ledger=(BASE/'00_进度/进度.md').read_text()
old={canonical(u) for u in re.findall(r'https?://[^\s|)>]+',ledger)}
entries=[
('S01','Android单调时钟','https://developer.android.com/reference/android/os/SystemClock',['return the time since','clock is guaranteed','elapsedRealtimeNanos\nAdded']),
('S02','GenerativeModel流式契约','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerativeModel',['finishReason\nwill','incremental','generateContentStream\n\(request','collect','only input request tokens']),
('S03','Candidate正文与终帧','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Candidate',['finishReason\n:', 'text\n:', 'partial','last']),
('S04','Prompt接入指南','https://developers.google.com/ml-kit/genai/prompt/android/get-started',['fullResponse','newChunkReceived','1.0.0-beta4']),
('S05','GenAI前台与资源限制','https://developers.google.com/ml-kit/genai',['foreground','quota','battery']),
('S06','结束原因常量','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Candidate.FinishReason',['const val\nMAX_TOKENS','const val\nSTOP']),
('S07','genai-prompt版本POM','https://dl.google.com/dl/android/maven2/com/google/mlkit/genai-prompt/1.0.0-beta4/genai-prompt-1.0.0-beta4.pom',['<version>']),
('S08','协程1.7.3超时源码','https://raw.githubusercontent.com/Kotlin/kotlinx.coroutines/1.7.3/kotlinx-coroutines-core/common/src/Timeout.kt',['public suspend fun <T> withTimeoutOrNull','asynchronous','Implementation note']),
('N01','GKE智能体会话容量','https://developers.googleblog.com/agents-are-sessions-not-requests-size-gke-node-pools-for-ai-agent-sessions/',['session','request','concurrency']),
('J01','腾讯CPU性能架构师详情API','https://careers.tencent.com/tencentcareer/api/post/ByPostId?postId=2013848487359307776',[]),
('J02','腾讯CPU性能架构师网页','https://careers.tencent.com/jobdesc.html?postId=2013848487359307776',[]),
('T01','Android Microbenchmark概览','https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview',['hot code paths','cache','Clocks on mobile devices','warmup'])]
results=[]
for sid,title,url,needles in entries:
 p=subprocess.run(['curl','-sL','--max-time','35','-w','\n%{http_code}',url],capture_output=True,text=True)
 body,_,code=p.stdout.rpartition('\n')
 content=re.search(r'<article\b[^>]*>(.*?)</article>',body,re.S)
 parser=Text(); parser.feed(content.group(1) if content else body)
 text='\n'.join(parser.out) if '<html' in body.lower() else body
 dates=re.findall(r'Last updated (\d{4}-\d{2}-\d{2})|"datePublished"\s*:\s*"([^"]+)"',body)
 excerpts=[]
 for needle in needles:
  matches=list(re.finditer(re.escape(needle),text,re.I))
  # 非正文导航会优先出现；取较靠后的两处方法/说明。
  for m in matches[-2:]: excerpts.append({'locator':needle,'excerpt':text[max(0,m.start()-100):m.end()+600]})
 details=None
 if sid=='J01' and code=='200':
  d=json.loads(body); details=d; excerpts=[{'locator':'Data职责/要求/更新时间','excerpt':json.dumps(d,ensure_ascii=False)}]
 row={'id':sid,'kind':'TOOL','title':title,'url':url,'canonical':canonical(url),'observed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'curl_exit':p.returncode,'http':code,'sha256':hashlib.sha256(body.encode()).hexdigest(),'source_dates':sorted(set(a or b for a,b in dates)),'read_state':'READ_BODY' if sid!='J02' and code=='200' else 'JS_SHELL_ONLY' if code=='200' else 'INACCESSIBLE','reuse':canonical(url) in old,'excerpts':excerpts}
 results.append(row)
 print('\n===',sid,'HTTP',code,'reuse',row['reuse'],'dates',row['source_dates'],'===')
 for e in excerpts: print(e['locator'],e['excerpt'])
 if p.returncode or code!='200': print('不可访问，不重试',p.stderr[:200])
(OUT/'sources.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
inputs=[]
for name in ['00_进度/进度.md','00_进度/智能体规则.md','02_AndroidAI/2026-11-18-端侧流式生成的Compose增量呈现.md']:
 path=BASE/name; inputs.append({'kind':'ARTIFACT','path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'read':'FULL','note':'昨日材料不是READY依赖，Android与全面验收均不假定通过' if '11-18' in name else ''})
(OUT/'inputs.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
