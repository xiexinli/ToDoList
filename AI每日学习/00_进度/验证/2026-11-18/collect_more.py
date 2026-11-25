import runpy,json
from pathlib import Path
E=Path(__file__).parent
# 复用采集函数；不执行原入口
ns={"__file__":str(E/"collect_sources.py")};s=(E/'collect_sources.py').read_text();exec(s[:s.index('res=list(')],ns)
pairs=[
('S08','https://developer.android.com/develop/ui/compose/state'),
('S09','https://developer.android.com/topic/libraries/architecture/coroutines'),
('S10','https://dl.google.com/dl/android/maven2/androidx/lifecycle/lifecycle-viewmodel-ktx/2.8.7/lifecycle-viewmodel-ktx-2.8.7.pom'),
('S11','https://dl.google.com/dl/android/maven2/androidx/lifecycle/lifecycle-runtime-compose/2.8.7/lifecycle-runtime-compose-2.8.7.pom'),
('S12','https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/1.3.0/material3-1.3.0.pom'),
('S13','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Candidate.FinishReason'),
('S14','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerateContentRequest.Builder'),
('S15','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/TextPart'),
('S16','https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Generation'),
('S17','https://raw.githubusercontent.com/Kotlin/kotlinx.coroutines/1.7.3/kotlinx-coroutines-core/common/src/Timeout.kt'),
('N01','https://developers.googleblog.com/build-full-stack-android-apps-with-gemini-in-google-ai-studio/'),
('J02','https://careers.tencent.com/tencentcareer/api/post/Query?keyword=%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%BA%94%E7%94%A8&pageIndex=1&pageSize=20'),
('T01','https://github.com/android/compose-samples'),
('T02','https://raw.githubusercontent.com/android/compose-samples/main/Jetchat/README.md'),
]
import concurrent.futures
res=list(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(ns['fetch'],pairs))
(E/'sources_more.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,ensure_ascii=False,indent=2))
print('\n====新动态实读====\n',(E/'N01.txt').read_text())
print('\n====工具README====\n',(E/'T02.txt').read_text())
print('\n====岗位候选====\n',(E/'J02.raw').read_text()[:17000])
