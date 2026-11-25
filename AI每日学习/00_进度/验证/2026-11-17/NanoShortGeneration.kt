// NOT_EXECUTED：实际ML Kit API接入片段，不是完整Android App。
// com.google.mlkit:genai-prompt:1.0.0-beta4；Android API >= 26。
// 需要已有Android应用与协程环境；禁止本次安装依赖/连接手机/下载模型。
import com.google.mlkit.genai.common.FeatureStatus
import com.google.mlkit.genai.common.GenAiException
import com.google.mlkit.genai.prompt.Candidate
import com.google.mlkit.genai.prompt.GenerateContentRequest
import com.google.mlkit.genai.prompt.Generation
import com.google.mlkit.genai.prompt.GenerativeModel
import com.google.mlkit.genai.prompt.TextPart
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.withTimeoutOrNull

// 应用自定义结果；不是Google SDK枚举。
data class ShortResult(val state: String, val text: String = "", val note: String = "")

suspend fun generateShortNote(
    raw: String,
    gatePassed: Boolean,              // 续用昨日can_attempt_local；不可写死true
    isTopForeground: () -> Boolean,  // 调用方提供当前证据，不是前台服务状态
    onState: (String) -> Unit,        // 映射给UI；必须不抛异常、不外发数据
    onCleanupFailure: () -> Unit     // 独立本地告警；不记录原文，必须不抛异常
): ShortResult {
    fun finish(state: String, text: String = "", note: String = ""): ShortResult {
        onState(state)
        return ShortResult(state, text, note)
    }
    currentCoroutineContext().ensureActive()
    val text = raw.trim()
    if (text.isEmpty()) return finish("EMPTY_INPUT")
    if (text.length > 120) return finish("INPUT_TOO_LONG") // 产品上限，不是Token计数
    if (!gatePassed) return finish("BLOCKED")
    if (!isTopForeground()) return finish("FOREGROUND_REQUIRED")
    var client: GenerativeModel? = null
    var stage = "CREATE"
    try {
        val model = Generation.getClient() // 不复用昨日finally中已close的实例
        client = model                    // 先记录引用，再进入可取消区间
        stage = "CHECK"
        onState("CHECKING")
        val status = withTimeoutOrNull(2500L) { model.checkStatus() }
            ?: return finish("CHECK_TIMEOUT")
        if (status != FeatureStatus.AVAILABLE) return finish("BLOCKED")
        if (!isTopForeground()) return finish("FOREGROUND_REQUIRED")
        val request = GenerateContentRequest.Builder(
            TextPart("请将下面的虚构便签改写成一句简洁中文，只返回改写文本：\n$text")
        ).apply {
            candidateCount = 1
            maxOutputTokens = 64  // Token预算，不保证64汉字，更不是时延保证
        }.build()
        stage = "GENERATE"
        onState("GENERATING")
        val response = withTimeoutOrNull(10000L) { model.generateContent(request) }
            ?: return finish("GENERATION_TIMEOUT")
        currentCoroutineContext().ensureActive()
        if (!isTopForeground()) return finish("FOREGROUND_REQUIRED")
        // 文档说candidates非空；仍防御空适配结果。只读取公开候选，不读取thoughtProcess。
        val candidate = response.candidates.firstOrNull()
        val output = candidate?.text.orEmpty().trim()
        if (output.isEmpty()) return finish("EMPTY_RESULT")
        return when (candidate?.finishReason) {
            Candidate.FinishReason.STOP -> finish("SUCCESS", output)
            Candidate.FinishReason.MAX_TOKENS -> finish("TRUNCATED", output)
            else -> finish("INCOMPLETE") // 不把OTHER/未知结束原因当完整成功
        }
    } catch (cancelled: CancellationException) {
        onState("CANCELLED")
        throw cancelled // Lifecycle/ViewModel取消继续向上；不触发云端或重试
    } catch (error: GenAiException) {
        // 保存数值错误码与阶段，不按message猜原因，不记录提示词/输出。
        return finish("FAILED", note = "$stage:SDK:${error.errorCode}")
    } catch (error: Exception) {
        return finish("FAILED", note = "$stage:${error.javaClass.simpleName}")
    } finally {
        try {
            client?.close()  // 每次调用独立生命周期；取消/超时/失败同样尝试释放
        } catch (_: Exception) {
            onCleanupFailure() // 不让清理错误掩盖原始失败或取消
        }
    }
}
