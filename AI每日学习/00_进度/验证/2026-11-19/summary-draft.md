11-19｜Android × AI第4讲：端侧生成的性能测量
① 用Android单调时钟，分别记录请求受理与生成开始；首字指首个非空白正文到达，不是屏幕已绘制。
② 最终帧也检查正文；正常收集结束才记完成，截断/异常/取消/超时隔离，无首字填null。
③ 同设备/冷热/前台/资源条件才统计；无真实输出Token数，不算tokens/s。
最值得看：Google强调按会话与相同CPU保证比较容量，11-16发布。
https://developers.googleblog.com/agents-are-sessions-not-requests-size-gke-node-pools-for-ai-agent-sessions/
动手：添加“相同正文但TIMEOUT不算快成功”测试，核对失败数与成功分位数。
验证：26个Host合成时序测试通过；Android编译/Nano真机性能未执行，合成数字不是模型实测。
