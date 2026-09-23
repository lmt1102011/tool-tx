package com.lmt.tooltx.ui.tool

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.lmt.tooltx.ForkInstaller
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentToolBinding
import com.lmt.tooltx.ui.home.HomeFragment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlin.math.roundToInt

class ToolFragment : Fragment() {

    @Volatile
    private var running = false
    private var lastCode: String? = null

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

        binding.btnBack.setOnClickListener {
            (requireActivity() as MainActivity).showFragment(HomeFragment::class.java, "home", push = false)
        }

        binding.btnOpenTool.setOnClickListener { startTool() }

        val bridge = (requireActivity() as MainActivity).getBridge()
        if (bridge.isLoggedIn()) startTool()
    }

    private fun startTool() {
        if (running) return
        running = true
        setStatus("Đang kết nối server...")
        setCode(null)

        GlobalScope.launch(Dispatchers.IO) {
            try {
                val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
                val session = bridge.getSession()
                if (session == null) {
                    withContext(Dispatchers.Main) {
                        if (_binding == null) return@withContext
                        setStatus("Chưa đăng nhập — đăng nhập trước.")
                    }
                    return@launch
                }
                val server = bridge.discoverServer() ?: "http://localhost:8787"
                val token = bridge.refreshToken() ?: session["idToken"]?.toString().orEmpty()
                bridge.clearKick()

                if (!ForkInstaller.isInstalled(requireContext())) {
                    val apk = withContext(Dispatchers.IO) {
                        ForkInstaller.prepareApk(requireContext(), server)
                    }
                    if (apk != null) {
                        val launched = ForkInstaller.install(requireContext(), apk)
                        withContext(Dispatchers.Main) {
                            if (_binding == null) return@withContext
                            if (launched) {
                                setStatus("Chưa cài Chromium Fork — đang mở màn hình CÀI ĐẶT...")
                                setAgent("Bấm CÀI ĐẶT (cho phép cài từ nguồn này nếu được hỏi), rồi mở TOOL lại.")
                            } else {
                                setStatus("Không mở được màn hình cài đặt.")
                            }
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            if (_binding == null) return@withContext
                            setStatus("Không tìm thấy file chromefork.apk.")
                            setAgent("Đặt chromefork.apk vào thư mục assets của app trước khi build, hoặc upload lên thư mục public của server.")
                        }
                    }
                    return@launch
                }

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
                            setAgent("Đăng nhập lại trong app rồi bấm MỞ TOOL.")
                        } else {
                            setStatus("Không lấy được mã liên kết — bấm MỞ TOOL lại.")
                            setAgent("Server bật nhưng không trả mã trong 10s.")
                        }
                    }
                    return@launch
                }
                lastCode = code
                val ok = bridge.startFork(server, code)
                withContext(Dispatchers.Main) {
                    if (_binding == null) return@withContext
                    setCode("Mã liên kết: $code")
                    if (ok) {
                        setStatus("Đã mở Chromium Fork — chờ kết nối CDP...")
                        setAgent("Agent fork đang chạy trên điện thoại.")
                    } else {
                        setStatus("Khởi động Chrome Fork thất bại.")
                        setAgent("Cài Chromium Fork rồi thử lại.")
                    }
                }
            } finally {
                running = false
            }
        }
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
        binding.tvCode.visibility = if (text.isNullOrEmpty()) android.view.View.GONE else android.view.View.VISIBLE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}