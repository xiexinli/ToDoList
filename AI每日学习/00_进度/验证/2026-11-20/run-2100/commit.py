import pathlib, re, hashlib, difflib
ROOT=pathlib.Path('/Users/alion/DemoProjects/ToDoList/AI每日学习')
def commit(day, topic, number, body, sources):
    run=ROOT/'00_进度/验证'/day/'run-2100'
    ledger=ROOT/'00_进度/进度.md'; old=ledger.read_text()
    matches=list((ROOT/'02_AndroidAI').glob(day+'-*.md'))
    if matches:
        path=matches[0]
        if len(matches)!=1: raise RuntimeError('多份旧日文件，停止覆盖')
        text=path.read_text(); print('保留已有主文件',path)
    else:
        path=ROOT/'02_AndroidAI'/f'{day}-{topic}.md'
        with path.open('x',encoding='utf-8') as f: f.write(body)
        text=body
    assert [int(x) for x in re.findall(r'^## ([0-5]) ',text,re.M)]==list(range(6))
    assert '📝 我的复述' in text
    rel=str(path.relative_to(ROOT)); new=old
    if not re.search(r'^\| '+re.escape(day)+r' \|',new,re.M):
        row=f'| {day} | 02_AndroidAI · 第 {number} 讲 | {topic} | {rel} | 待填 |\n'
        marker='\n\n> 欠产与补写记录：'
        assert marker in new; new=new.replace(marker,'\n'+row+marker,1)
    plan=f'- [x] Android × AI · 第 {number} 讲：{topic}（{day} 材料已产出；EXECUTED_HOST纯策略fixture通过，SDK/设备/云模型NOT_EXECUTED；复述待填）'
    if not any(topic in line for line in new.split('## 本周计划')[1].split('## 动态链接去重表')[0].splitlines()):
        new=new.replace('## 动态链接去重表',plan+'\n\n## 动态链接去重表',1)
    # 当天所有引用登记；已出现的教学参考以续用记录说明，不重复首次行
    rows=[]; continued=[]
    for title,url in sources:
        if url not in new: rows.append(f'| {day} | {title} | {url} |')
        else: continued.append(f'[{title}]({url})')
    marker='\n## 周总结'
    addition='\n'+'\n'.join(rows)+f'\n\n> {day} 补写于2026-11-21；来源小摘录与本轮HTTP抽验：`验证/{day}/run-2100/sources-small.json`；代码与Host日志同目录；本执行者摘要not_sent，由主智能体验收后提交。'
    if continued: addition+=' 教学参考续用（非新动态）：'+'；'.join(continued)+'。'
    if f'> {day} 补写于' not in new: new=new.replace(marker,addition+'\n'+marker,1)
    backup=run/'ledger.before.md'
    if not backup.exists(): backup.write_text(old)
    diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='ledger.before',tofile='ledger.after'))
    (run/'ledger.diff').write_text(diff)
    if new!=old: ledger.write_text(new,encoding='utf-8')
    count=sum('\u4e00' <= c <= '\u9fff' for c in text)
    report=f'day={day}\nfile={path}\ncjk={count}\nledger_sha256={hashlib.sha256(ledger.read_bytes()).hexdigest()}\ndiff_sha256={hashlib.sha256(diff.encode()).hexdigest()}\n'
    (run/'commit.log').write_text(report); print(report)
