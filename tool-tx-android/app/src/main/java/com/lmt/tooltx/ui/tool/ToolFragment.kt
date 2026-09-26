package com.lmt.tooltx.ui.tool

import android.animation.ValueAnimator
import android.content.pm.ActivityInfo
import android.os.Bundle
import android.text.Spannable
import android.text.SpannableStringBuilder
import android.text.style.ForegroundColorSpan
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.webkit.WebView
import android.widget.LinearLayout
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.lmt.tooltx.AppUpdater
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
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlin.math.roundToInt

class ToolFragment : Fragment() {

    @Volatile
    private var running = false
    private var startJob: Job? = null
    private var lastCode: String? = null
    private var gameOpen = false
    private var gameUrl: String? = null
    private var pendingOpen = false
    private var muted = true

    @Volatile
    private var lastPanel: Map<*, *> = emptyMap<String, Any?>()
    private var countdownJob: Job? = null
    private var barAnimator: ValueAnimator? = null
    private var blinkAnimator: ValueAnimator? = null
    private var splashJob: Job? = null
    private var pollJob: Job? = null
    private var openBtnReadyShown = false
    private var connectedReady = false
    private var toolStarted = false
    private var noDataTicks = 0
    private var missStreak = 0

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
        binding.btnExitGame.setOnClickListener { closeGame() }
        binding.btnBack.setOnClickListener {
            if (gameOpen) {
                closeGame()
            } else {
                (requireActivity() as MainActivity).showFragment(HomeFragment::class.java, "home", push = false)
            }
        }
binding.predCard.setOnTouchListener(::onDragTouch)
        setupWebView()

        val bridge = (requireActivity() as MainActivity).getBridge()
        binding.tvLivePick.text = getString(R.string.phase_press_open_game)
        if (bridge.isLoggedIn()) startTool() else setOpenBtnReady(false)

        backCallback = object : androidx.activity.OnBackPressedCallback(false) {
            override fun handleOnBackPressed() {
                if (gameOpen) {
                    closeGame()
                } else {
                    isEnabled = false
                    requireActivity().onBackPressedDispatcher.onBackPressed()
                }
            }
        }
        requireActivity().onBackPressedDispatcher.addCallback(viewLifecycleOwner, backCallback!!)
        startCountdownTicker()
        setupUpdater()
    }

    // ── Tự cập nhật: check GitHub, hiện card dưới card server, tải + cài ngay trong app ──
    private fun setupUpdater() {
        val ctx = context ?: return
        binding.btnUpdateLater.setOnClickListener {
            AppUpdater.markSeen(ctx, pendingRelease?.versionName ?: return@setOnClickListener)
            binding.cardUpdate.visibility = View.GONE
        }
        binding.btnUpdateNow.setOnClickListener { downloadUpdate() }
        checkUpdate()
    }

    private var pendingRelease: AppUpdater.Release? = null

    private fun checkUpdate(force: Boolean = false) {
        val ctx = context ?: return
        GlobalScope.launch {
            val release = runCatching { AppUpdater.check(ctx, force) }.getOrNull()
            withContext(Dispatchers.Main) {
                if (_binding == null || release == null) return@withContext
                pendingRelease = release
                val sizeText = if (release.size > 0) {
                    " • " + getString(R.string.update_size, formatSize(release.size))
                } else ""
                binding.tvUpdateVersion.text =
                    getString(R.string.update_version, release.versionName, AppUpdater.versionName(ctx)) + sizeText
                val notes = release.notes.trim()
                if (notes.isNotEmpty()) {
                    binding.tvUpdateNotes.text = notes
                    binding.tvUpdateNotes.visibility = View.VISIBLE
                } else {
                    binding.tvUpdateNotes.visibility = View.GONE
                }
                binding.pbUpdate.visibility = View.GONE
                binding.btnUpdateNow.isEnabled = true
                binding.btnUpdateNow.text = getString(R.string.update_now)
                binding.btnUpdateLater.visibility = View.VISIBLE
                binding.cardUpdate.visibility = View.VISIBLE
            }
        }
    }

    private fun formatSize(bytes: Long): String {
        val mb = bytes / (1024.0 * 1024.0)
        return if (mb >= 1) String.format(Locale.US, "%.1f MB", mb)
        else String.format(Locale.US, "%.0f KB", bytes / 1024.0)
    }

    private fun downloadUpdate() {
        val ctx = context ?: return
        val release = pendingRelease ?: return
        binding.btnUpdateNow.isEnabled = false
        binding.btnUpdateLater.visibility = View.GONE
        binding.pbUpdate.visibility = View.VISIBLE
        binding.pbUpdate.progress = 0
        GlobalScope.launch {
            try {
                val apk = AppUpdater.download(ctx, release) { percent, _, _ ->
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        binding.pbUpdate.progress = percent
                        binding.btnUpdateNow.text = getString(R.string.update_downloading, percent)
                    }
                }
                withContext(Dispatchers.Main) {
                    if (_binding != null) {
                        binding.btnUpdateNow.text = getString(R.string.update_downloaded)
                        setStatus(getString(R.string.update_installing))
                    }
                }
                AppUpdater.install(ctx, apk)
                AppUpdater.markSeen(ctx, release.versionName)
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    if (_binding == null) return@withContext
                    binding.pbUpdate.visibility = View.GONE
                    binding.btnUpdateNow.isEnabled = true
                    binding.btnUpdateNow.text = getString(R.string.update_now)
                    binding.btnUpdateLater.visibility = View.VISIBLE
                    setStatus(getString(R.string.update_failed, e.message ?: "lỗi mạng"))
                }
            }
        }
    }

    private var backCallback: androidx.activity.OnBackPressedCallback? = null

    private fun setSystemUiFullscreen(fullscreen: Boolean) {
        val window = requireActivity().window
        if (fullscreen) {
            androidx.core.view.WindowCompat.setDecorFitsSystemWindows(window, false)
            if (android.os.Build.VERSION.SDK_INT >= 28) {
                try {
                    window.attributes = window.attributes.apply {
                        layoutInDisplayCutoutMode =
                            android.view.WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
                    }
                } catch (_: Exception) {}
            }
            window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            val controller = androidx.core.view.WindowCompat.getInsetsController(window, window.decorView)
            controller.systemBarsBehavior =
                androidx.core.view.WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            controller.hide(androidx.core.view.WindowInsetsCompat.Type.systemBars())
        } else {
            window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            if (android.os.Build.VERSION.SDK_INT >= 28) {
                try {
                    window.attributes = window.attributes.apply {
                        layoutInDisplayCutoutMode =
                            android.view.WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_DEFAULT
                    }
                } catch (_: Exception) {}
            }
            val controller = androidx.core.view.WindowCompat.getInsetsController(window, window.decorView)
            controller.systemBarsBehavior =
                androidx.core.view.WindowInsetsControllerCompat.BEHAVIOR_DEFAULT
            controller.show(androidx.core.view.WindowInsetsCompat.Type.systemBars())
            androidx.core.view.WindowCompat.setDecorFitsSystemWindows(window, true)
        }
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
                return true
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
                isDragging = false
                return true
            }
        }
        return false
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
        s.javaScriptCanOpenWindowsAutomatically = true
        s.setSupportMultipleWindows(true)
        s.useWideViewPort = true
        s.loadWithOverviewMode = true
        s.cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
        s.userAgentString = DESKTOP_UA
        s.mediaPlaybackRequiresUserGesture = false
        s.textZoom = 100
        android.webkit.CookieManager.getInstance().setAcceptCookie(true)
        android.webkit.CookieManager.getInstance().setAcceptThirdPartyCookies(wv, true)
        try {
            if (android.os.Build.VERSION.SDK_INT >= 24) {
                android.webkit.ServiceWorkerController.getInstance().setServiceWorkerClient(
                    object : android.webkit.ServiceWorkerClient() {
                        override fun shouldInterceptRequest(
                            request: android.webkit.WebResourceRequest
                        ): android.webkit.WebResourceResponse? = null
                    }
                )
            }
        } catch (_: Throwable) {}
        wv.webViewClient = object : android.webkit.WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: android.webkit.WebResourceRequest?
            ): Boolean {
                return false
            }

            override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                return false
            }

            override fun onPageStarted(
                view: WebView,
                url: String,
                favicon: android.graphics.Bitmap?
            ) {
                WebViewBridge.installWsShim()
                WebViewBridge.setMuted(muted)
                setStatus("Game đang tải…")
            }

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                WebViewBridge.installWsShim()
                WebViewBridge.setMuted(muted)
                WebViewBridge.armMute()
                WebViewBridge.unstickGame()
                scheduleSplashWatchdog()
            }

            override fun onReceivedError(
                view: WebView,
                request: android.webkit.WebResourceRequest,
                error: android.webkit.WebResourceError
            ) {
                super.onReceivedError(view, request, error)
                if (request.isForMainFrame) {
                    setStatus("Lỗi tải game: " + (error.description ?: "").toString())
                }
            }

            override fun onRenderProcessGone(
                view: WebView,
                detail: android.webkit.RenderProcessGoneDetail
            ): Boolean {
                setStatus("Game bị treo — đang tải lại...")
                val u = gameUrl
                if (u != null) WebViewBridge.navigate(u) else WebViewBridge.reloadGame()
                return true
            }
        }
        wv.webChromeClient = object : android.webkit.WebChromeClient() {
            override fun onCreateWindow(
                view: WebView,
                isDialog: Boolean,
                isUserGesture: Boolean,
                resultMsg: android.os.Message
            ): Boolean {
                wv.post {
                    val transport = resultMsg.obj as? WebView.WebViewTransport
                    transport?.webView = wv
                    resultMsg.sendToTarget()
                }
                return true
            }
        }
        WebViewBridge.attach(wv)
    }

    private fun scheduleSplashWatchdog() {
        splashJob?.cancel()
        splashJob = GlobalScope.launch(Dispatchers.IO) {
            delay(12000)
            if (_binding == null || !gameOpen) return@launch
            if (WebViewBridge.isStuckOnSplash()) {
                WebViewBridge.unstickGame()
                delay(8000)
                if (_binding == null || !gameOpen) return@launch
                if (WebViewBridge.isStuckOnSplash()) {
                    withContext(Dispatchers.Main) {
                        if (_binding != null) setStatus("Game đang kẹt ở màn giới thiệu — tải lại...")
                    }
                    WebViewBridge.hardReloadGame()
                }
            }
        }
    }

    companion object {
        private const val DESKTOP_UA =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                "Chrome/131.0.0.0 Safari/537.36"
    }

    // ── Flow: nút MỞ TOOL → MỞ GAME → mở game fullscreen ngang ─
    private fun onOpenGameClicked() {
        if (gameOpen) {
            closeGame()
            return
        }
        // Nút này chỉ hiện khi đã kết nối xong, nên tuyệt đối không gọi lại startTool
        // (gọi lại sẽ khởi động agent mới và làm mất nút).
        if (connectedReady || openBtnReadyShown) {
            if (gameUrl != null) {
                openGame()
            } else {
                pendingOpen = true
                setStatus("Đã kết nối — đang chờ mã game...")
            }
            return
        }
        if (!running) {
            startTool()
        } else {
            setStatus("Đang kết nối server — chờ 1 chút rồi tự mở game.")
        }
    }

    // ── Mở game ─────────────────────────────────────────────────
    private fun openGame() {
        if (gameOpen) return
        val url = gameUrl
        if (url.isNullOrEmpty()) {
            setStatus("Chưa có mã game — chờ lấy mã rồi bấm lại.")
            return
        }
        gameOpen = true
        noDataTicks = 0
        pendingOpen = false
        backCallback?.isEnabled = true
        binding.toolPage.visibility = View.GONE
        binding.gameOverlay.visibility = View.VISIBLE
        val wv = binding.webView
        wv.visibility = View.VISIBLE
        WebViewBridge.attach(wv)
        WebViewBridge.navigate(url)
        WebViewBridge.setMuted(muted)
        requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        (requireActivity() as MainActivity).setGameFullscreen(true)
        setSystemUiFullscreen(true)
        binding.btnOpenTool.text = getString(R.string.close_game)
        binding.btnOpenTool.visibility = View.VISIBLE
        setStatus("Đang tải game — tool sẽ tự bắt dữ liệu, chờ vài giây...")
    }

    private fun closeGame() {
        if (!gameOpen) return
        gameOpen = false
        noDataTicks = 0
        backCallback?.isEnabled = false
        binding.gameOverlay.visibility = View.GONE
        binding.toolPage.visibility = View.VISIBLE
        splashJob?.cancel()
        val wv = binding.webView
        try { wv.stopLoading() } catch (_: Exception) {}
        wv.visibility = View.GONE
        try { wv.loadUrl("about:blank") } catch (_: Exception) {}
        try { wv.clearHistory() } catch (_: Exception) {}
        WebViewBridge.detach()
        requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
        (requireActivity() as MainActivity).setGameFullscreen(false)
        setSystemUiFullscreen(false)
        val socketConnected = connectedReady || runCatching { (requireActivity() as MainActivity).getBridge().isSocketConnected() }.getOrDefault(false)
        setOpenBtnReady(socketConnected) // đã kết nối → MỞ GAME xanh; chưa → MỞ CÔNG CỤ
        if (socketConnected) setStatus("Server: đã kết nối — bấm MỞ GAME để chơi.")
        else setStatus("Chưa kết nối — bấm MỞ GAME để kết nối.")
    }

    private fun startTool(forceRefresh: Boolean = false) {
        startJob?.cancel()
        pollJob?.cancel()
        running = true
        missStreak = 0
        if (_binding != null) binding.btnOpenTool.isEnabled = false
        if (forceRefresh && gameOpen) {
            gameOpen = false
            backCallback?.isEnabled = false
            pendingOpen = true
            binding.gameOverlay.visibility = View.GONE
            binding.toolPage.visibility = View.VISIBLE
            wvGone()
            requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
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
                bridge.writeBugLog("ui", "startTool: server=$server forceRefresh=$forceRefresh")
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

                var connected = false
                var curServer = server
                // Thử tối đa 3 lần: mỗi lần fail → rediscover (bỏ cache) để bắt tunnel URL mới,
                // vì launcher có thể đã đổi URL khi server restart.
                for (attempt in 1..3) {
                    try {
                        bridge.disconnectSocket()
                        bridge.connectSocket(curServer, token)
                    } catch (_: Exception) {}
                    connected = bridge.isSocketConnected()
                    bridge.writeBugLog("ui", "connect attempt=$attempt server=$curServer connected=$connected")
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        setStatus(
                            if (connected) "Server: $curServer — lấy mã liên kết..."
                            else "Đang thử kết nối server... ($attempt/3)"
                        )
                    }
                    if (connected) break
                    if (attempt < 3) {
                        // Server chưa kịp cập nhật URL → ép tìm lại (không dùng cache).
                        val freshServer = bridge.discoverServer(force = true)
                        if (!freshServer.isNullOrEmpty()) curServer = freshServer
                        delay(3000)
                    }
                }

                if (!connected) {
                    bridge.writeBugLog("ui", "ket qua: KHONG ket noi duoc server (sau 3 lan)")
                    // Thử 1 lần cuối với URL mới nhất từ config.txt/đăng ký.
                    val lastTry = bridge.discoverServer(force = true) ?: curServer
                    try {
                        bridge.disconnectSocket()
                        bridge.connectSocket(lastTry, token)
                    } catch (_: Exception) {}
                    connected = bridge.isSocketConnected()
                    if (connected) curServer = lastTry
                    bridge.writeBugLog("ui", "final try server=$lastTry connected=$connected")
                }

                if (!connected) {
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        setStatus("Không kết nối được server: $curServer")
                        setAgent("Kiểm tra: server đã bật trên PC, điện thoại cùng mạng Wi-Fi với PC, và địa chỉ server đúng. Nếu server vừa restart, chờ 10–30 giây rồi bấm MỞ GAME lại.")
                        stopToolButtons()
                    }
                    return@launch
                }

                val code = bridge.getAgentPair(curServer)
                bridge.writeBugLog("ui", "agent_code=" + (code ?: "NULL"))
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
                val ok = bridge.startAgent(curServer, code)
                bridge.writeBugLog("ui", "startAgent ok=" + ok)
                withContext(Dispatchers.Main) {
                    if (_binding == null) return@withContext
                    setCode("Mã liên kết: $code")
                    if (ok) {
                        toolStarted = true
                        setStatus("Đã kết nối — bấm MỞ GAME để chơi.")
                        setAgent("Chờ game mở rồi chơi ngay trong app.")
                        binding.btnOpenTool.isEnabled = true
                        setOpenBtnReady(true)
                    } else {
                        setStatus("Không khởi động được agent.")
                        setAgent("Thử bấm RESET MÃ rồi bấm MỞ CÔNG CỤ.")
                        stopToolButtons()
                    }
                }
                if (ok) pollAgentStatus(bridge, gameOpen)
            } finally {
                running = false
            }
        }
    }

    private fun stopToolButtons() {
        toolStarted = false
        missStreak = 0
        connectedReady = false
        binding.btnOpenTool.isEnabled = true
        setOpenBtnReady(false)
    }

    // Nút lớn dưới tool: luôn hiện — chưa chạy tool → "MỞ CÔNG CỤ" (màu thường),
    // đã chạy → "MỞ GAME" màu xanh lá. Không bao giờ ẩn đi.
    private fun setOpenBtnReady(ready: Boolean) {
        openBtnReadyShown = ready
        binding.btnOpenTool.text = getString(if (ready) R.string.open_game else R.string.open_tool)
        binding.btnOpenTool.backgroundTintList = ContextCompat.getColorStateList(
            requireContext(),
            if (ready) R.color.panelGo else R.color.primary
        )
        if (binding.btnOpenTool.visibility != View.VISIBLE) {
            binding.btnOpenTool.alpha = 0f
            binding.btnOpenTool.visibility = View.VISIBLE
            binding.btnOpenTool.animate().alpha(1f).setDuration(180).start()
        }
    }

    private fun pollAgentStatus(bridge: PythonBridge, gameOpenAtStart: Boolean) {
        pollJob?.cancel()
        pollJob = GlobalScope.launch(Dispatchers.IO) {
            while (isActive) {
                if (_binding == null) return@launch
                val st = bridge.agentStatus()
                val msg = st["message"]?.toString()?.takeIf { it.isNotEmpty() } ?: ""
                val connected = st["connected"]?.toString()?.toBooleanStrictOrNull() ?: false
                val url = st["url"]?.toString()?.takeIf { it.isNotEmpty() }
                if (url != null) gameUrl = url

                val panel = bridge.getLastPanel()
                if (panel.isNotEmpty()) {
                    val pick = panel["pick"]?.toString()?.trim().orEmpty()
                    val hist = (panel["hist"] as? List<*>)?.size ?: 0
                    bridge.writeBugLog("ui", "panel: pick=$pick hist=$hist")
                    withContext(Dispatchers.Main) {
                        if (_binding != null) prediction(panel)
                    }
                }
                withContext(Dispatchers.Main) {
                    if (_binding == null) return@withContext
                    if (msg.isNotEmpty()) setAgent(msg)
                    connectedReady = connected
                    if (connected) {
                        missStreak = 0
                        binding.btnOpenTool.isEnabled = true
                        if (gameOpen) {
                            binding.btnOpenTool.text = getString(R.string.close_game)
                            if (binding.btnOpenTool.visibility != View.VISIBLE) {
                                binding.btnOpenTool.visibility = View.VISIBLE
                            }
                        } else {
                            if (!openBtnReadyShown) setOpenBtnReady(true)
                            if (gameUrl != null) {
                                setStatus(getString(R.string.ready_press_game))
                                if (pendingOpen && !gameOpen) {
                                    pendingOpen = false
                                    openGame()
                                }
                            } else {
                                setStatus("Đã kết nối — đang chờ mã game...")
                            }
                        }
                    } else {
                        // Không ẩn nút khi rớt kết nối, chỉ báo trạng thái và tự nối lại.
                        missStreak++
                        binding.btnOpenTool.isEnabled = true
                        if (missStreak >= 3 && toolStarted && !gameOpen) {
                            setStatus("Mất kết nối — đang kết nối lại...")
                        } else if (msg.isNotEmpty()) {
                            setStatus(msg)
                        }
                    }
                    // Game đang mở: cài lại shim mỗi vòng (game có thể tự reload/navigation)
                    // và tự thử lại nếu lâu không có dữ liệu.
                    if (gameOpen) {
                        WebViewBridge.installWsShim()
                        val p = panel
                        val gotData = !p.isEmpty() && (
                            !p["pick"].toString().isNullOrBlank() ||
                                ((p["hist"] as? List<*>)?.size ?: 0) > 0 ||
                                (p["rStart"]?.toString()?.toDoubleOrNull() ?: 0.0) > 0 ||
                                (p["lastResult"]?.toString()?.isNotBlank() == true)
                            )
                        noDataTicks = if (gotData) 0 else noDataTicks + 1
                        if (noDataTicks == 8) {
                            WebViewBridge.unstickGame()
                            WebViewBridge.armMute()
                            setStatus(getString(R.string.hint_retry_data))
                            binding.btnOpenTool.text = getString(R.string.close_game)
                        } else if (noDataTicks >= 20) {
                            setStatus(getString(R.string.hint_reset_data))
                        }
                    }
                }
                delay(2000)
            }
        }
    }

    private fun wvGone() {
        val wv = binding.webView
        try { wv.stopLoading() } catch (_: Exception) {}
        wv.visibility = View.GONE
    }

    override fun onResume() {
        super.onResume()
        if (_binding != null && pendingRelease != null) checkUpdate(force = true)
        if (gameOpen) {
            requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            (requireActivity() as MainActivity).setGameFullscreen(true)
            setSystemUiFullscreen(true)
            WebViewBridge.resumeWebView()
        }
    }

    override fun onPause() {
        super.onPause()
        WebViewBridge.pauseWebView()
    }

    override fun onStop() {
        super.onStop()
        // Bấm Home / app switcher → phải TẮT game, không được chạy ngầm.
        if (gameOpen) {
            closeGame()
        } else {
            WebViewBridge.pauseWebView()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        countdownJob?.cancel()
        countdownJob = null
        splashJob?.cancel()
        splashJob = null
        pollJob?.cancel()
        pollJob = null
        toolStarted = false
        stopBarAnim()
        stopBlinkAnim()
        lastPanel = emptyMap<String, Any?>()
        connectedReady = false
        openBtnReadyShown = false
        WebViewBridge.detach()
        runCatching { (activity as? MainActivity)?.getBridge()?.stopAgent() }
        if (gameOpen) {
            gameOpen = false
            backCallback?.isEnabled = false
            requireActivity().requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
            setSystemUiFullscreen(false)
        }
        _binding = null
    }

    private fun prediction(p: Map<*, *>) {
        if (p.isEmpty()) return
        lastPanel = p
        renderPhase(p)
    }

    private fun isTai(v: String): Boolean =
        v.startsWith("T", ignoreCase = true) && !v.startsWith("X", ignoreCase = true)

    // Vẽ panel dự đoán giống web PC: phase + countdown (Server ước lượng phiên) +
    // thanh tỉ lệ TÀI/XỈU đôi. Phiên đầu (skipFirst, pick null) vẫn hiện countdown/kết quả.
    private fun renderPhase(p: Map<*, *>) {
        if (_binding == null) return
        val ctx = requireContext()
        val now = System.currentTimeMillis()
        fun num(k: String): Double =
            (p[k] as? Number)?.toDouble() ?: (p[k]?.toString()?.toDoubleOrNull() ?: 0.0)

        val rStart = num("rStart").toLong()
        val rEnd = num("rEnd").toLong()
        val lastSettle = num("lastSettle").toLong()
        val roundDur = num("roundDur")
        val interGap = num("interGap").let { if (it > 0) it else 18.0 }
        val lastResult = (p["lastResult"] as? String)?.trim().orEmpty()
        val realSum = num("realSum").toInt()
        val pick = p["pick"]?.toString()?.trim()
        val confV = num("confidence").let { if (it > 0) it else num("conf") }
        val isSkip = (p["skip"] as? Boolean) ?: (p["skip"]?.toString()?.toBooleanStrictOrNull() ?: false)
        val isSkipFirst = (p["skipFirst"] as? Boolean)
            ?: (p["skipFirst"]?.toString()?.toBooleanStrictOrNull() ?: false) || (isSkip && pick.isNullOrEmpty())
        val roundN = num("roundN").toInt()
        val settledPick = (p["settledPick"] as? String)?.trim()?.takeIf { it.isNotEmpty() }
        val settledWin = (p["settledWin"] as? Boolean)
            ?: (p["settledWin"]?.toString()?.toBooleanStrictOrNull() ?: false)
        val settledResult = (p["settledResult"] as? String)?.trim()?.takeIf { it.isNotEmpty() }
        val settledSum = num("settledSum").toInt()
        var pT = num("pT")
        var pX = num("pX")
        if (pT <= 0 && pX <= 0) { pT = 50.0; pX = 50.0 }

        val betLen = if (rStart > 0 && rEnd > rStart) (rEnd - rStart) / 1000.0 else roundDur
        val revShow = (if (betLen > 0) betLen else 0.0) + interGap - 3.0
        val sRound = if (rStart > 0) (now - rStart) / 1000.0 else -1.0
        val live = rStart > 0

        val phase: String = if (live) {
            when {
                sRound < 3.0 -> "wait"
                sRound < betLen - 15.0 -> "analyze"
                sRound < betLen - 2.0 -> "ready"
                sRound < betLen -> "get_result"
                sRound < revShow -> "reveal"
                else -> "wait"
            }
        } else {
            "idle"
        }
        val phaseColorRes = when {
            isSkipFirst && phase != "reveal" && phase != "idle" -> R.color.panelWarn
            else -> when (phase) {
                "ready" -> if (isSkip) R.color.panelWarn else R.color.panelGo
                "reveal" -> R.color.panelGo
                "get_result" -> R.color.panelWarn
                "analyze" -> R.color.panelAnalyze
                else -> R.color.panelDim
            }
        }
        val phaseColor = ContextCompat.getColor(ctx, phaseColorRes)

        val remaining = Math.max(0L, (rEnd - now) / 1000L)
        val nextStart = if (lastSettle > 0) lastSettle + (interGap * 1000.0).toLong() else 0L
        val toNext = if (nextStart > now) Math.max(0L, (nextStart - now) / 1000L) else 0L
        fun countdownTxt(): String = when {
            remaining > 0 -> getString(R.string.panel_countdown_remaining, remaining)
            toNext > 0 -> getString(R.string.panel_new_round_in, toNext)
            else -> getString(R.string.panel_estimated)
        }

        val pickTai = pick != null && isTai(pick)
        val hasData = !pick.isNullOrEmpty() || realSum > 0 || lastResult.isNotEmpty() || rStart > 0
        val noDataTxt: String = if (gameOpen) {
            getString(R.string.phase_wait_game_data)
        } else if (openBtnReadyShown) {
            getString(R.string.phase_press_open_game)
        } else {
            getString(R.string.phase_stabilizing)
        }
        val predText: String
        val predColor: Int
        when {
            phase == "reveal" -> {
                val resSide = settledResult ?: lastResult
                // CHỈ hiện tổng của ĐÚNG vòng vừa sổ. Không fallback sang realSum
                // (đó là tổng vòng trước → sinh ra "XỈU tổng 11" do lệch phiên).
                val showSum = settledSum
                val side = getString(if (isTai(resSide)) R.string.tai else R.string.xiu)
                if (!settledPick.isNullOrEmpty()) {
                    val predSide = getString(if (isTai(settledPick)) R.string.tai else R.string.xiu)
                    val verdict = getString(if (settledWin) R.string.panel_settled_correct else R.string.panel_settled_wrong)
                    predText = if (showSum > 0) {
                        getString(R.string.panel_settled_line, predSide, side, showSum, verdict)
                    } else {
                        getString(R.string.panel_settled_line_nosum, predSide, side, verdict)
                    }
                    predColor = ContextCompat.getColor(ctx, if (settledWin) R.color.panelGo else R.color.panelTai)
                } else {
                    predText = if (showSum > 0) {
                        getString(R.string.panel_result_with_sum, side, showSum)
                    } else {
                        getString(R.string.phase_result) + ": " + side
                    }
                    predColor = ContextCompat.getColor(ctx, R.color.panelGo)
                }
            }
            isSkipFirst && phase != "reveal" -> {
                predText = getString(R.string.panel_skip_first)
                predColor = ContextCompat.getColor(ctx, R.color.panelWarn)
            }
            phase == "analyze" -> {
                predText = getString(R.string.phase_analyze)
                predColor = ContextCompat.getColor(ctx, R.color.panelAnalyze)
            }
            phase == "ready" && !pick.isNullOrEmpty() -> {
                predText = if (confV > 0) {
                    getString(
                        R.string.panel_pick_with_conf,
                        getString(if (pickTai) R.string.tai else R.string.xiu),
                        confV
                    )
                } else {
                    getString(if (pickTai) R.string.tai else R.string.xiu)
                }
                predColor = ContextCompat.getColor(ctx, if (pickTai) R.color.panelTai else R.color.panelXiu)
            }
            phase != "idle" -> {
                predText = ""
                predColor = ContextCompat.getColor(ctx, R.color.panelText)
            }
            !hasData -> {
                predText = if (gameOpen) noDataTxt else getString(R.string.pick_open_game)
                predColor = ContextCompat.getColor(ctx, R.color.panelDim)
            }
            else -> {
                predText = getString(R.string.waiting_data)
                predColor = ContextCompat.getColor(ctx, R.color.panelDim)
            }
        }

        val statusTxt: String
        val countTxt: String
        when (phase) {
            "idle" -> {
                statusTxt = noDataTxt
                countTxt = ""
            }
            "wait" -> {
                statusTxt = getString(R.string.phase_wait)
                countTxt = countdownTxt()
            }
            "analyze" -> {
                statusTxt = ""
                countTxt = countdownTxt()
            }
            "ready" -> {
                statusTxt = when {
                    pick.isNullOrEmpty() -> noDataTxt
                    roundN > 0 -> getString(R.string.panel_session, roundN)
                    else -> ""
                }
                countTxt = countdownTxt()
            }
            "get_result" -> {
                statusTxt = getString(R.string.phase_get_result)
                countTxt = countdownTxt()
            }
            else -> { statusTxt = getString(R.string.phase_result); countTxt = "" }
        }

        binding.tvPrediction.text = predText
        binding.tvPrediction.setTextColor(predColor)
        if (phase == "analyze" && !isSkipFirst) {
            startBlinkAnim()
        } else {
            stopBlinkAnim()
        }
        binding.tvCountdown.text = countTxt
        binding.tvCountdown.setTextColor(phaseColor)
        binding.tvPercentage.text = statusTxt
        binding.tvPercentage.setTextColor(phaseColor)
        val liveTxt = if (hasData) {
            if (predText.isNotEmpty()) predText else countTxt
        } else if (gameOpen) {
            getString(R.string.phase_wait_game_data)
        } else {
            getString(R.string.phase_press_open_game)
        }
        binding.tvLivePick.text = liveTxt
        binding.tvLivePick.setTextColor(
            if (hasData) predColor else ContextCompat.getColor(ctx, R.color.onSurfaceVariant)
        )
        if (phase == "analyze") startBarAnim() else { stopBarAnim(); setBar(pT, pX) }
        renderHistory(p)
    }

    private fun startBlinkAnim() {
        if (blinkAnimator != null && blinkAnimator!!.isStarted) return
        val a = ValueAnimator.ofFloat(0.35f, 1f).apply {
            duration = 900L
            repeatMode = ValueAnimator.REVERSE
            repeatCount = ValueAnimator.INFINITE
            addUpdateListener { va ->
                if (_binding != null) binding.tvPrediction.alpha = va.animatedValue as Float
            }
        }
        blinkAnimator = a
        a.start()
    }

    private fun stopBlinkAnim() {
        blinkAnimator?.cancel()
        blinkAnimator = null
        if (_binding != null) binding.tvPrediction.alpha = 1f
    }

    private fun startBarAnim() {
        if (barAnimator != null && barAnimator!!.isStarted) return
        val a = ValueAnimator.ofFloat(3f, 85f).apply {
            duration = 1300L
            repeatMode = ValueAnimator.REVERSE
            repeatCount = ValueAnimator.INFINITE
            addUpdateListener { va ->
                val t = (va.animatedValue as Float).toDouble()
                if (_binding != null) setBar(t, 100.0 - t)
            }
        }
        barAnimator = a
        a.start()
    }

    private fun stopBarAnim() {
        barAnimator?.cancel()
        barAnimator = null
    }

    private fun setBar(pT: Double, pX: Double) {
        if (_binding == null) return
        val tW = pT.coerceIn(0.0, 85.0).roundToInt()
        val xW = (100 - tW).coerceIn(0, 100)
        (binding.barTai.layoutParams as LinearLayout.LayoutParams).weight = tW.toFloat()
        (binding.barXiu.layoutParams as LinearLayout.LayoutParams).weight = xW.toFloat()
        binding.barTai.requestLayout()
        binding.barXiu.requestLayout()
    }

    private fun renderHistory(p: Map<*, *>) {
        if (_binding == null) return
        val hist = p["hist"] ?: p["history"]
        if (hist !is List<*>) {
            binding.tvHistory.text = ""
            return
        }
        val ctx = requireContext()
        val taiC = ContextCompat.getColor(ctx, R.color.panelTai)
        val xiuC = ContextCompat.getColor(ctx, R.color.panelXiu)
        val dimC = ContextCompat.getColor(ctx, R.color.panelDim)
        // 14 cầu gần nhất, hiển thị dạng "TXTTXXT..." (mới nhất bên phải).
        val recent = hist.mapNotNull { sideChar(it?.toString()) }.takeLast(14)
        if (recent.isEmpty()) {
            binding.tvHistory.text = getString(R.string.hist_empty)
            binding.tvHistory.setTextColor(dimC)
            return
        }
        val sb = SpannableStringBuilder(recent.joinToString(" "))
        for ((i, ch) in recent.withIndex()) {
            val start = i * 2
            sb.setSpan(
                ForegroundColorSpan(if (ch == 'T') taiC else xiuC),
                start, start + 1, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
            )
        }
        binding.tvHistory.text = sb
    }

    // Một ký hiệu cầu: 'T' hoặc 'X'. Chấp nhận cả dạng chữ ("T","XỈU") lẫn dạng
    // tổng xúc xắc dạng số (3..18; >= 11 là TÀI) cho chắc chắn dải lịch sử không bị trống.
    private fun sideChar(raw: String?): Char? {
        val ch = (raw ?: "").trim().uppercase(Locale.ROOT)
        if (ch.isEmpty()) return null
        if (isTai(ch)) return 'T'
        if (ch.startsWith("X")) return 'X'
        val n = ch.toIntOrNull() ?: return null
        if (n < 3 || n > 18) return null
        return if (n >= 11) 'T' else 'X'
    }

    // Cập nhật countdown mỗi giây từ panel cuối (server ước lượng phiên).
    private fun startCountdownTicker() {
        countdownJob?.cancel()
        countdownJob = GlobalScope.launch(Dispatchers.IO) {
            while (!Thread.currentThread().isInterrupted) {
                val p = lastPanel
                if (p.isNotEmpty() && _binding != null && gameOpen) {
                    withContext(Dispatchers.Main) {
                        if (_binding != null && gameOpen) renderPhase(p)
                    }
                }
                delay(1000)
            }
        }
    }

    private fun setStatus(text: String) {
        binding.tvToolStatus.text = text
        binding.tvBottomStatus.text = text
    }

    private fun setAgent(text: String) {
        binding.tvAgentStatus.text = text
        binding.tvBottomStatus.text = text
    }

    private fun setCode(text: String?) {
        binding.tvCode.text = text.orEmpty()
        binding.tvCode.visibility = if (text.isNullOrEmpty()) View.GONE else View.VISIBLE
    }
}