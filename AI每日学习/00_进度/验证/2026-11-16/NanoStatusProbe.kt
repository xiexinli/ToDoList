// NOT_EXECUTED：官方契约核对的 Android 接入片段，不是独立 App。
// SDK：com.google.mlkit:genai-prompt:1.0.0-beta4；Android API >= 26。
// 此文件只查询状态，不下载模型，不推理，不上传提示词。
import com.google.mlkit.genai.common.FeatureStatus
import com.google.mlkit.genai.prompt.Generation
import com.google.mlkit.genai.prompt.GenerativeModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withTimeoutOrNull

// 以下是应用自己的状态，不是 SDK 提供的枚举。
enum class NanoReadiness {
    AVAILABLE, DOWNLOADABLE, DOWNLOADING, UNAVAILABLE, UNKNOWN, QUERY_FAILED
}

data class NanoObservation(val readiness: NanoReadiness, val note: String = "")

suspend fun readNanoReadiness(): NanoObservation {
    var client: GenerativeModel? = null
    return try {
        val model = Generation.getClient()  // 成功创建客户端不代表模型可用
        client = model
        // 2500 ms 是教学选择的 UI 等待预算，不是 SDK 时延承诺。
        val raw = withTimeoutOrNull(2500L) { model.checkStatus() }
        when (raw) {
            FeatureStatus.AVAILABLE -> NanoObservation(NanoReadiness.AVAILABLE)
            FeatureStatus.DOWNLOADABLE -> NanoObservation(NanoReadiness.DOWNLOADABLE)
            FeatureStatus.DOWNLOADING -> NanoObservation(NanoReadiness.DOWNLOADING)
            FeatureStatus.UNAVAILABLE -> NanoObservation(NanoReadiness.UNAVAILABLE)
            null -> NanoObservation(NanoReadiness.QUERY_FAILED, "状态查询超时")
            else -> NanoObservation(NanoReadiness.UNKNOWN, "未识别的 SDK 状态")
        }
    } catch (cancelled: CancellationException) {
        // ViewModel/生命周期取消是控制信号，不吞掉、不变成云端重试。
        throw cancelled
    } catch (e: Exception) {
        // 不用错误文案猜设备型号，也不把异常映射成 AVAILABLE。
        NanoObservation(NanoReadiness.QUERY_FAILED, "状态查询失败：${e.javaClass.simpleName}")
    } finally {
        client?.close()  // 一次性探测样例；该实例不能再用于明日推理
    }
}
