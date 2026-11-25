// SPEC_CHECK，NOT_EXECUTED：接入片段，不是完整App；本次不安装/编译/连手机。
// 版本证据：genai-prompt 1.0.0-beta4；lifecycle 2.8.7；material3 1.3.0。
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.google.mlkit.genai.common.FeatureStatus
import com.google.mlkit.genai.common.GenAiException
import com.google.mlkit.genai.prompt.Candidate
import com.google.mlkit.genai.prompt.GenerateContentRequest
import com.google.mlkit.genai.prompt.Generation
import com.google.mlkit.genai.prompt.GenerativeModel
import com.google.mlkit.genai.prompt.TextPart
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeoutOrNull

// 全部是应用状态，不是SDK枚举；不暴露/读取思考过程。
data class StreamUi(
    val requestId: Long = 0,
    val status: String = "IDLE",
    val draft: String = "",
    val notice: String = ""
) {
    val busy get() = status == "CHECKING" || status == "STREAMING"
    val canAccept get() = status == "SUCCESS" && draft.isNotBlank()
}
private class ForegroundLost : Exception()

class NanoStreamViewModel : ViewModel() {
    private val mutableUi = MutableStateFlow(StreamUi())
    val ui = mutableUi.asStateFlow() // Compose只读不可变快照
    private var epoch = 0L
    private var job: Job? = null
    private val singleFlight = Mutex()
    var cleanupFailures = 0
        private set // 本地计数，不记录提示词/输出/原异常消息

    private fun publish(id: Long, value: StreamUi) {
        if (id == epoch) mutableUi.value = value // 拒收旧请求的迟到结果/取消状态
    }

    // 调用方约束：这些入口只在Main线程使用；VM按当前页面作用域创建。
    fun start(raw: String, gatePassed: Boolean, isTopForeground: () -> Boolean) {
        val id = ++epoch
        job?.cancel() // 旧任务先失效；新任务在锁内等待旧finally完成
        mutableUi.value = StreamUi(id, "CHECKING")
        job = viewModelScope.launch {
            singleFlight.withLock {
                currentCoroutineContext().ensureActive()
                if (id != epoch) return@withLock
                var client: GenerativeModel? = null // 资源引用在所有超时块外
                var local = StreamUi(id, "CHECKING")
                var terminal: Int? = null
                var stage = "CREATE"
                fun state(status: String, notice: String = "") {
                    local = local.copy(status = status, notice = notice)
                    publish(id, local)
                }
                try {
                    val input = raw.trim()
                    if (input.isEmpty()) { state("EMPTY_INPUT"); return@withLock }
                    if (input.length > 120) { state("INPUT_TOO_LONG"); return@withLock }
                    if (!gatePassed) { state("BLOCKED"); return@withLock }
                    if (!isTopForeground()) throw ForegroundLost()
                    val model = Generation.getClient() // 不复用昨日已close实例
                    client = model
                    stage = "CHECK"
                    val status = withTimeoutOrNull(2500L) { model.checkStatus() }
                    if (status == null) { state("CHECK_TIMEOUT"); return@withLock }
                    if (status != FeatureStatus.AVAILABLE) {
                        state("BLOCKED"); return@withLock
                    }
                    if (!isTopForeground()) throw ForegroundLost()
                    val request = GenerateContentRequest.Builder(
                        TextPart("请将虚构便签改写成一句简洁中文，只返回改写文本：\n$input")
                    ).apply { candidateCount = 1; maxOutputTokens = 64 }.build()
                    stage = "STREAM"
                    state("STREAMING")
                    val complete = withTimeoutOrNull(10000L) {
                        model.generateContentStream(request).collect { response ->
                            currentCoroutineContext().ensureActive()
                            if (id != epoch) throw CancellationException("旧请求失效")
                            if (!isTopForeground()) throw ForegroundLost()
                            if (terminal != null) error("终止标记后仍有帧")
                            val candidate = response.candidates.singleOrNull()
                                ?: error("候选数量违反单候选契约")
                            // 指南明确 +=：text是新增片段；最终帧也先追加再读结束原因。
                            local = local.copy(draft = local.draft + candidate.text.orEmpty())
                            terminal = candidate.finishReason
                            publish(id, local) // 不trim逐片文本，不按内容distinct
                        }
                        true // 最终标记出现不立刻SUCCESS，等collect正常完成
                    }
                    currentCoroutineContext().ensureActive()
                    if (!isTopForeground()) throw ForegroundLost()
                    if (complete == null) {
                        state("GENERATION_TIMEOUT", "未完成草稿已隔离")
                    } else {
                        val end = when (terminal) {
                            Candidate.FinishReason.STOP ->
                                if (local.draft.isBlank()) "EMPTY_RESULT" else "SUCCESS"
                            Candidate.FinishReason.MAX_TOKENS -> "TRUNCATED"
                            else -> "INCOMPLETE"
                        }
                        state(end, if (end == "SUCCESS") "" else "未完成草稿已隔离")
                    }
                } catch (cancelled: CancellationException) {
                    state("CANCELLED", "未完成草稿已隔离")
                    throw cancelled // 取消不转成成功、重试或上云
                } catch (_: ForegroundLost) {
                    state("FOREGROUND_REQUIRED", "未完成草稿已隔离")
                } catch (error: GenAiException) {
                    state("FAILED", "$stage:SDK:${error.errorCode}；草稿已隔离")
                } catch (_: Exception) {
                    state("FAILED", "$stage:应用契约失败；草稿已隔离")
                } finally {
                    try { client?.close() } catch (_: Exception) { cleanupFailures++ }
                    // close尝试失败不掩盖原错；Mutex解锁不证明设备资源已释放。
                }
            }
        }
    }

    fun stop() {
        if (job?.isActive == true) {
            ++epoch // 发布权限先撤销；旧catch/finally不能污染当前UI
            mutableUi.value = mutableUi.value.copy(
                status = "CANCELLED", notice = "未完成草稿已隔离"
            )
            job?.cancel()
        }
    }
    // ViewModel清理会取消viewModelScope；请求finally负责close，不重复启动推理。
}

@Composable
fun NanoStreamScreen(
    vm: NanoStreamViewModel, // 页面作用域实例，由已有工程的调用方提供
    gatePassed: Boolean,    // 续用第1讲，禁止写死true
    isAppTopForeground: () -> Boolean // 应用最上层前台证据，不是前台服务状态
) {
    val owner = LocalLifecycleOwner.current
    val topForeground by rememberUpdatedState(isAppTopForeground)
    val state by vm.ui.collectAsStateWithLifecycle(
        lifecycleOwner = owner, minActiveState = Lifecycle.State.RESUMED
    )
    var input by rememberSaveable { mutableStateOf("先完成今天最重要的小事") }
    DisposableEffect(owner, vm) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_PAUSE || event == Lifecycle.Event.ON_DESTROY) {
                vm.stop() // 停UI订阅不等于停止VM里的生成，必须明确取消请求
            }
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer); vm.stop() }
    }
    Column {
        OutlinedTextField(value = input, onValueChange = { vm.stop(); input = it })
        Button(onClick = {
            vm.start(input, gatePassed) {
                owner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED) && topForeground()
            }
        }) { Text(if (state.busy) "替换当前请求" else "本地生成") }
        Button(onClick = { vm.stop() }, enabled = state.busy) { Text("停止") }
        Text(state.status)
        // 失败/截断/取消草稿留在VM，默认不作为正文展示，更不能自动覆盖原文。
        Text(if (state.status == "STREAMING" || state.canAccept) state.draft else state.notice)
        Button(onClick = { input = state.draft }, enabled = state.canAccept) { Text("采纳") }
    }
}
