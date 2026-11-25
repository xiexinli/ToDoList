// SPEC_CHECK，NOT_EXECUTED：不是独立App；不含Compose/流式拼接/模型下载。
// com.google.mlkit:genai-prompt:1.0.0-beta4；协程核心1.7.3；Android API>=26。
import android.os.SystemClock
import com.google.mlkit.genai.prompt.Candidate
import com.google.mlkit.genai.prompt.GenerateContentRequest
import com.google.mlkit.genai.prompt.GenerativeModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.withTimeoutOrNull

data class LatencyRecord(
    val requestNs: Long,
    val generationNs: Long?,
    val firstBodyNs: Long?,
    val finishMarkerNs: Long?,
    val observedEndNs: Long,
    val status: String,
    val clock: String = "ANDROID_ELAPSED_REALTIME_NS"
) // 原始单调时间，不记录正文/提示词/思考过程；统计与分组在测量后做。
private class BadTimeline : Exception()
private class ForegroundLost : Exception()

suspend fun measureReadyStream(
    model: GenerativeModel, // 调用方已做门禁，拥有客户端并在外层finally尝试close
    request: GenerateContentRequest, // 已构建；candidateCount=1
    requestNs: Long, // 用户请求受理时的elapsedRealtimeNanos；在排队/门禁之前
    budgetMs: Long,
    isTopForeground: () -> Boolean, // 实际最上层前台证据，不是前台服务
    report: (LatencyRecord) -> Unit // 必须不抛错/不挂起；本地收下记录，稍后写文件
) {
    require(budgetMs > 0L) // 预算与条件一起登记，不能只保留跑得完的样本
    var generation: Long? = null
    var first: Long? = null
    var marker: Long? = null
    var reason: Int? = null
    var last = requestNs
    var end: Long? = null
    var status = "ERROR"
    fun stamp(): Long {
        val now = SystemClock.elapsedRealtimeNanos()
        if (requestNs < 0L || now < last) throw BadTimeline()
        last = now
        return now
    }
    try {
        currentCoroutineContext().ensureActive()
        if (!isTopForeground()) throw ForegroundLost()
        val completed = withTimeoutOrNull(budgetMs) {
            generation = stamp() // 即将开始collect；不是只测创建冷Flow对象
            model.generateContentStream(request).collect { response ->
                val arrival = stamp() // 第一行取时间：在检查/记录/渲染之前
                currentCoroutineContext().ensureActive()
                if (!isTopForeground()) throw ForegroundLost()
                if (marker != null) throw BadTimeline() // 标记后再来帧：契约异常
                val candidate = response.candidates.singleOrNull() ?: throw BadTimeline()
                if (first == null && candidate.text.orEmpty().isNotBlank()) first = arrival
                // 最终帧先查正文，不能只看结束原因；不读取推理过程。
                reason = candidate.finishReason
                if (reason != null) marker = arrival
            }
            end = stamp() // collect正常返回的时刻；不同于STOP到达
            true
        }
        currentCoroutineContext().ensureActive()
        if (!isTopForeground()) throw ForegroundLost()
        if (completed == null) {
            end = stamp(); status = "TIMEOUT" // 自己预算超时，非完整耗时
        } else {
            status = when (reason) {
                Candidate.FinishReason.STOP -> if (first != null) "SUCCESS" else "EMPTY_RESULT"
                Candidate.FinishReason.MAX_TOKENS -> "TRUNCATED"
                else -> "INCOMPLETE"
            }
        }
    } catch (cancelled: CancellationException) {
        end = SystemClock.elapsedRealtimeNanos(); status = "CANCELLED"
        throw cancelled // 外部取消（含外层超时）继续传播；原因由调用方另记
    } catch (_: ForegroundLost) {
        end = SystemClock.elapsedRealtimeNanos(); status = "ENV_INVALID"
    } catch (_: BadTimeline) {
        end = SystemClock.elapsedRealtimeNanos(); status = "INVALID"
    } catch (_: Exception) {
        end = SystemClock.elapsedRealtimeNanos(); status = "ERROR"
    } finally {
        report(LatencyRecord(requestNs, generation, first, marker,
            end ?: SystemClock.elapsedRealtimeNanos(), status))
        // report之后由外层记录close耗时/错误；不将释放时间混入生成完成时长。
    }
}
