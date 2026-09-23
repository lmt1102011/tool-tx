package com.lmt.tooltx.ui.tool

import android.content.pm.ActivityInfo
import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.WebViewBridge
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentToolBinding
import com.lmt.tooltx.ui.home.HomeFragment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlin.math.roundToInt

class ToolFragment : Fragment() {

    @Volatile
    private var running = false
    private var startJob: Job? = null
    private var lastCode: String? = null
    private var panelExpanded = true
    private var gameOpen = false
    private var gameUrl: String? = null
    private var pendingOpen = false

    private var _binding: FragmentToolBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentToolBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnOpenTool.setOnClickListener { onOpenGameClicked() }
        binding.btnResetToken.setOnClickListener { startTool(forceRefresh = true) }
        binding.panelHeader.setOnTouchListener(::onDragTouch)
        binding.btnTogglePanel.setOnClickListener { togglePanel() }
        binding.btnBack.setOnClickListener {
            if (gameOpen) {
                closeGame()
            } else {
                (requireActivity() as MainActivity).showFragment(HomeFragment::class.java, "home", push = false)
            }
        }
        setupWebView()

        val bridge = (requireActivity() as MainActivity).getBridge()
        if (bridge.isLoggedIn()) startTool()
    }

    // ── Cửa sổ dự đoán kéo thả ───────────────────────────────
    private var downRawX = 0f
    private var downRawY = 0f
    private var startTransX = 0f
    private var startTransY = 0f
    private var isDragging = false

    private fun onDragTouch(v: View, e: MotionEvent): Boolean {
        val card = binding.predCard
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                downRawX = e.rawX; downRawY = e.rawY
                startTransX = card.translationX; startTransY = card.translationY
                isDragging = false
                return false
            }
            MotionEvent.ACTION_MOVE -> {
                val dx = e.rawX - downRawX
                val dy = e.rawY - downRawY
                if (kotlin.math.abs(dx) > 6f || kotlin.math.abs(dy) > 6f) isDragging = true
                if (isDragging) card.translationX = startTransX + dx
                if (isDragging) card.translationY = startTransY + dy
                return true
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                if (!isDragging) togglePanel()
                return true
            }
        }
        return false
    }

    private fun togglePanel() {
        panelExpanded = !panelExpanded
        binding.panelBody.visibility = if (panelExpanded) View.VISIBLE else View.GONE
        binding.btnTogglePanel.rotation = if (panelExpanded) 0f else 180f
    }

    private fun setupWebView() {
        val wv = binding.webView
        val s = wv.settings
        s.javaScriptEnabled = true
        s.domStorageEnabled = true
        s.databaseEnabled = true
        s.loadsImagesAutomatically = true
        s.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        s.setSupportZoom(false)
        android.webkit.CookieManager.getInstance().setAcceptCookie(true)
        android.webkit.CookieManager.getInstance().setAcceptThirdPartyCookies(wv, true)
        wv.setBackgroundColor(Color.parseColor("#000000"))
        WebViewBridge.attach(wv)
    }

    // ── Flow: setup → kết nối → mở game fullscreen ngang ─────
    private fun onOpenGameClicked() {
        if (gameOpen) {
            closeGame()
            return
        }
        pendingOpen = true
        val bridge = (requireActivity() as MainActivity).getBridge()
        if (bridge.isSocketConnected() && gameUrl != null) {
            openGame()
        } else if (!running) {
            startTool()
        } else {
            setStatus("Đang kết nối server — chờ 1 chút rồi tự mở game.")
        }
    }

    private fun openGame() {
        if (gameOpen) return
        gameOpen = true
        pendingOpen = false
        val wv = binding.webView
        wv.visibility = View.VISIBLE
        WebViewBridge.attach(wv)
        gameUrl?.let { WebViewBridge.navigate(it) }
        requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        binding.btnOpenTool.text = "ĐÓNG GAME"
        setStatus("Đang chơi — cửa sổ dự đoán kéo thả được.")
    }

    private fun closeGame() {
        if (!gameOpen) return
        gameOpen = false
        binding.webView.visibility = View.GONE
        requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        binding.btnOpenTool.text = "MỞ GAME"
        if (running) setStatus("Server: đã kết nối — bấm MỞ GAME để chơi.")
        else setStatus("Chưa kết nối — bấm MỞ GAME để kết nối.")
    }

    private fun startTool(forceRefresh: Boolean = false) {
        startJob?.cancel()
        running = true
        if (forceRefresh && gameOpen) {
            gameOpen = false
            pendingOpen = true
            binding.webView.visibility = View.GONE
            requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
            binding.btnOpenTool.text = "MỞ GAME"
        }
        setStatus(if (forceRefresh) "Đang làm mới mã và kết nối lại server..." else "Đang kết nối server...")
        setCode(null)

        startJob = GlobalScope.launch(Dispatchers.IO) {
            try {
                val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
                val session = bridge.getSession()
                if (session == null) {
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        setStatus("Chưa đăng nhập — đăng nhập trước.")
                        stopToolButtons()
                    }
                    return@launch
                }
                val server = bridge.discoverServer() ?: "http://localhost:8787"
                if (forceRefresh) {
                    bridge.stopAgent()
                    bridge.disconnectSocket()
                }
                val token = if (forceRefresh) {
                    bridge.forceRefreshToken() ?: bridge.refreshToken()
                } else {
                    bridge.refreshToken()
                } ?: session["idToken"]?.toString().orEmpty()
                bridge.clearKick()

                for (attempt in 1..2) {
                    try {
                        bridge.disconnectSocket()
                        bridge.connectSocket(server, token)
                    } catch (_: Exception) {}
                    val connected = bridge.isSocketConnected()
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        setStatus(
                            if (connected) "Server: $server — lấy mã liên kết..."
                            else "Đang thử kết nối server... ($attempt/2)"
                        )
                    }
                    if (connected) break
                    delay(2500)
                }

                if (!bridge.isSocketConnected()) {
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        setStatus("Không kết nối được server: $server")
                        setAgent("Kiểm tra: server đã bật trên PC, điện thoại cùng mạng Wi-Fi với PC, và địa chỉ server đúng.")
                        stopToolButtons()
                    }
                    return@launch
                }

                val code = bridge.getAgentPair(server)
                if (code.isNullOrEmpty()) {
                    val kick = bridge.getLastKick()
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        if (!kick.isNullOrEmpty()) {
                            setStatus("Server từ chối: $kick")
                            setAgent("Bấm RESET MÃ để làm mới mã đăng nhập rồi kết nối lại.")
                        } else {
                            setStatus("Không lấy được mã liên kết — bấm RESET MÃ rồi MỞ GAME lại.")
                            setAgent("Server bật nhưng không trả mã trong 10s.")
                        }
                        stopToolButtons()
                    }
                    return@launch
                }
                lastCode = code
                val ok = bridge.startAgent(server, code)
                withContext(Dispatchers.Main) {
                    if (_binding == null) return@withContext
                    setCode("Mã liên kết: $code")
                    if (ok) {
                        setStatus("Đã kết nối — bấm MỞ GAME để chơi.")
                        setAgent("Chờ game mở rồi chơi ngay trong app.")
                        binding.btnOpenTool.isEnabled = true
                    } else {
                        setStatus("Không khởi động được agent.")
                        setAgent("Thử bấm RESET MÃ lại.")
                        stopToolButtons()
                    }
                }
                if (ok) pollAgentStatus(bridge)
            } finally {
                running = false
            }
        }
    }

    private fun stopToolButtons() {
        binding.btnOpenTool.isEnabled = false
        binding.btnOpenTool.text = "MỞ GAME"
    }

    private fun pollAgentStatus(bridge: PythonBridge) {
        GlobalScope.launch(Dispatchers.IO) {
            while (!Thread.currentThread().isInterrupted) {
                if (_binding == null) return@launch
                val st = bridge.agentStatus()
                val msg = st["message"]?.toString()?.takeIf { it.isNotEmpty() } ?: ""
                val connected = st["connected"]?.toString()?.toBooleanStrictOrNull() ?: false
                val url = st["url"]?.toString()?.takeIf { it.isNotEmpty() }
                if (url != null) gameUrl = url

                val panel = bridge.getLastPanel()
                if (panel.isNotEmpty()) {
                    withContext(Dispatchers.Main) {
                        if (_binding != null) prediction(panel)
                    }
                }
                withContext(Dispatchers.Main) {
                    if (_binding == null) return@withContext
                    if (msg.isNotEmpty()) setAgent(msg)
                    if (connected) {
                        binding.btnOpenTool.isEnabled = true
                        if (gameOpen) {
                            binding.btnOpenTool.text = "ĐÓNG GAME"
                        } else {
                            binding.btnOpenTool.text = "MỞ GAME"
                            if (gameUrl != null) {
                                setStatus("Đã kết nối — bấm MỞ GAME để chơi.")
                                if (pendingOpen && !gameOpen) openGame()
                            } else {
                                setStatus("Đã kết nối — đang chờ mã game...")
                            }
                        }
                    } else {
                        stopToolButtons()
                    }
                }
                delay(2000)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (gameOpen) requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        WebViewBridge.detach()
        runCatching { (activity as? MainActivity)?.getBridge()?.stopAgent() }
        if (gameOpen) requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        _binding = null
    }

    private fun prediction(p: Map<*, *>) {
        if (p.isEmpty()) return
        val pick = p["pick"]?.toString()?.trim()
        if (pick.isNullOrEmpty()) return

        val isTai = pick.equals("T", ignoreCase = true)
        binding.tvPrediction.text = if (isTai) "TÀI" else "XỈU"
        binding.tvPrediction.setTextColor(
            ContextCompat.getColor(
                requireContext(),
                if (isTai) R.color.error else R.color.primary
            )
        )

        val pT = p["pT"]?.toString()?.toDoubleOrNull() ?: (if (isTai) 60.0 else 40.0)
        val pX = p["pX"]?.toString()?.toDoubleOrNull() ?: (100.0 - pT)
        binding.tvPercentage.text = String.format(Locale.ROOT, "TÀI %02.0f  /  XỈU %02.0f", pT, pX)
        binding.progressBar.progress = pT.roundToInt().coerceIn(0, 100)

        val conf = (p["confidence"] ?: p["conf"])?.toString()?.toDoubleOrNull()
        val confTxt = conf?.let { String.format(Locale.ROOT, "Độ tin cậy %02.0f%%", it) }.orEmpty()

        val hist = p["hist"] ?: p["history"]
        var histTxt = ""
        if (hist is List<*>) {
            histTxt = hist.takeLast(16).joinToString("   ") { item ->
                (item?.toString()?.take(1) ?: "").uppercase()
            }
        }
        binding.tvHistory.text = listOf(confTxt, histTxt)
            .filter { it.isNotEmpty() }
            .joinToString(" | ")
    }

    private fun setStatus(text: String) {
        binding.tvToolStatus.text = text
    }

    private fun setAgent(text: String) {
        binding.tvAgentStatus.text = text
    }

    private fun setCode(text: String?) {
        binding.tvCode.text = text.orEmpty()
        binding.tvCode.visibility = if (text.isNullOrEmpty()) View.GONE else View.VISIBLE
    }
}