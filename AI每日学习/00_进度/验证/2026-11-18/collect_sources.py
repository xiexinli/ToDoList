import concurrent.futures, subprocess, pathlib, json, re, hashlib, datetime
from html.parser import HTMLParser
E=pathlib.Path(__file__).parent
sources=[
('S01','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerativeModel'),
('S02','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/common/StreamingCallback'),
('S03','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerateContentResponse'),
('S04','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Candidate'),
('S05','https://developers.google.com/ml-kit/genai/prompt/android/get-started'),
('S06','https://developers.google.com/ml-kit/genai'),
('S07','https://dl.google.com/dl/android/maven2/com/google/mlkit/genai-prompt/1.0.0-beta4/genai-prompt-1.0.0-beta4.pom'),
('D01','https://developers.googleblog.com/feeds/posts/default'),
('D02','https://android-developers.googleblog.com/feeds/posts/default'),
('J01','https://careers.tencent.com/tencentcareer/api/post/Query?keyword=%E7%AB%AF%E4%BE%A7&pageIndex=1&pageSize=10'),
]
class Text(HTMLParser):
 def __init__(self): super().__init__(); self.out=[]; self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'): self.skip+=1
  if t in ('p','div','tr','h1','h2','h3','li','pre','br'): self.out.append('\n')
 def handle_endtag(self,t):
  if t in ('script','style'): self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip:self.out.append(d)
def fetch(pair):
 sid,url=pair
 r=subprocess.run(['curl','-sL','--max-time','50','-w','\n%{http_code}',url],capture_output=True)
 body,_,code=r.stdout.rpartition(b'\n'); decoded=body.decode('utf-8','replace')
 p=Text();p.feed(decoded);text=re.sub(r'\n\s*\n+', '\n', ''.join(p.out))
 # Keep full article main only, not global navigation.
 m=re.search(r'<(?:article|main)\b[^>]*>(.*?)</(?:article|main)>',decoded,re.S)
 if m:
  p=Text();p.feed(m.group(1));text=re.sub(r'\n\s*\n+', '\n',''.join(p.out))
 (E/(sid+'.txt')).write_text(text)
 if sid.startswith(('D','J')):(E/(sid+'.raw')).write_bytes(body)
 info={'id':sid,'url':url,'http':code.decode(),'curl_exit':r.returncode,'observed_at':datetime.datetime.now().astimezone().isoformat(),'sha256':hashlib.sha256(body).hexdigest(),'datePublished':re.findall(r'"datePublished"\s*:\s*"([^"]+)',decoded),'last_updated':re.findall(r'Last updated[^<\n]*',decoded),'read_state':'DOWNLOADED_PENDING_READ'}
 return info
res=list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(fetch,sources))
(E/'sources_initial.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,ensure_ascii=False,indent=2))
