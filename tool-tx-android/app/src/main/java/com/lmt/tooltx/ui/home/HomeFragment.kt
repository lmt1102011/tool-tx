package com.lmt.tooltx.ui.home

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.SystemClock
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import com.chaquo.python.PyObject
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentHomeBinding
import com.lmt.tooltx.ui.settings.SettingsFragment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!
    private var lastRefresh = 0L
    private var updateCheckDone = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnProfile.setOnClickListener {
            (requireActivity() as MainActivity).showFragment(SettingsFragment::class.java, "settings")
        }

        binding.swipeRefresh.setOnRefreshListener { refresh(force = true) }
        binding.swipeRefresh.setColorSchemeResources(R.color.primary)

        binding.btnUpdate.setOnClickListener { startUpdateDownload() }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh(force: Boolean = false) {
        val now = SystemClock.elapsedRealtime()
        if (!force && lastRefresh != 0L && now - lastRefresh < 6000) return
        val first = lastRefresh == 0L
        lastRefresh = now
        if (first) {
            try {
                binding.skeleton.visibility = View.VISIBLE
                binding.skeleton.startShimmer()
            } catch (_: Exception) {}
        }
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            val session = bridge.getSession()
            val user = bridge.getUserData()
            val picks = if (user.isEmpty() || user.containsKey("error")) -1 else pickCount(user)
            val connected = bridge.isSocketConnected()

            // Check for app updates (only once per session unless forced)
            val currentVersion = getCurrentVersion()
            val updateInfo = if (!updateCheckDone || force) {
                updateCheckDone = true
                bridge.checkAppUpdate(currentVersion)
            } else {
                mapOf("has_update" to false)
            }

            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.swipeRefresh.isRefreshing = false
                b.skeleton.stopShimmer()
                b.skeleton.visibility = View.GONE
                val name = session?.get("displayName")?.toString()
                    ?: session?.get("username")?.toString()
                    ?: "Name"
                greet(name)

                val role = (user["role"] ?: session?.get("role"))?.toString().orEmpty()
                if (role.equals("admin", ignoreCase = true)) {
                    (requireActivity() as MainActivity).showAdmin(true)
                    credit("vô hạn", warn = false)
                    gate(null)
                } else {
                    (requireActivity() as MainActivity).showAdmin(false)
                    if (picks >= 0) {
                        val warn = picks <= 0
                        credit(picks.toString(), warn)
                        if (warn) {
                            gate("BẠN ĐÃ HẾT LƯỢT SỬ DỤNG TOOL — nạp thêm tại trang web để tiếp tục.")
                        } else {
                            gate(null)
                        }
                    } else {
                        credit("--", warn = false)
                        gate(null)
                    }
                }

                if (connected) {
                    server("Máy chủ đang hoạt động", ok = true)
                } else {
                    server("Máy chủ đang tắt", ok = false)
                }

                // Handle update card
                val hasUpdate = updateInfo["has_update"] == true
                b.cardUpdate.visibility = if (hasUpdate) View.VISIBLE else View.GONE
                if (hasUpdate) {
                    val latestVersion = updateInfo["latest_version"]?.toString() ?: ""
                    val notes = updateInfo["release_notes"]?.toString() ?: ""
                    b.tvUpdateTitle.text = "Có phiên bản mới v$latestVersion"
                    b.tvUpdateDesc.text = if (notes.isNotEmpty()) notes else "Bấm để tải và cài đặt"
                }
            }
        }
    }

    private fun getCurrentVersion(): String {
        return try {
            requireContext().packageManager.getPackageInfo(requireContext().packageName, 0).versionName
        } catch (_: Exception) {
            "0.0.0"
        }
    }

    private fun startUpdateDownload() {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            val currentVersion = getCurrentVersion()
            val updateInfo = bridge.checkAppUpdate(currentVersion)
            val downloadUrl = updateInfo["download_url"]?.toString()

            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                if (downloadUrl.isNullOrEmpty()) {
                    Toast.makeText(requireContext(), "Không tìm thấy link tải APK", Toast.LENGTH_SHORT).show()
                    return@withContext
                }

                b.btnUpdate.isEnabled = false
                b.btnUpdate.text = "ĐANG TẢI..."

                downloadAndInstallApk(downloadUrl, b)
            }
        }
    }

    private fun downloadAndInstallApk(downloadUrl: String, b: FragmentHomeBinding) {
        GlobalScope.launch(Dispatchers.IO) {
            try {
                val url = URL(downloadUrl)
                val connection = url.openConnection() as HttpURLConnection
                connection.connectTimeout = 15000
                connection.readTimeout = 30000
                val fileLength = connection.contentLength

                val input = connection.inputStream
                val outputFile = File(requireContext().cacheDir, "tool-tx-update.apk")
                val output = FileOutputStream(outputFile)

                val buffer = ByteArray(8192)
                var total = 0
                var len: Int

                while (input.read(buffer).also { len = it } != -1) {
                    output.write(buffer, 0, len)
                    total += len

                    val progress = if (fileLength > 0) (total * 100 / fileLength) else 0
                    withContext(Dispatchers.Main) {
                        if (b == _binding) {
                            b.btnUpdate.text = "ĐANG TẢI $progress%"
                        }
                    }
                }

                output.flush()
                output.close()
                input.close()

                withContext(Dispatchers.Main) {
                    val b2 = _binding ?: return@withContext
                    b2.btnUpdate.text = "ĐANG CÀI ĐẶT..."
                    installApk(outputFile)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    val b2 = _binding ?: return@withContext
                    b2.btnUpdate.isEnabled = true
                    b2.btnUpdate.text = "CẬP NHẬT"
                    Toast.makeText(requireContext(), "Lỗi tải APK: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun installApk(apkFile: File) {
        val intent = Intent(Intent.ACTION_VIEW)
        val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            FileProvider.getUriForFile(
                requireContext(),
                "${requireContext().packageName}.fileprovider",
                apkFile
            )
        } else {
            Uri.fromFile(apkFile)
        }
        intent.setDataAndType(uri, "application/vnd.android.package-archive")
        intent.flags = Intent.FLAG_GRANT_READ_URI_PERMISSION
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        // Use the launcher intent to restart after install
        val activity = requireActivity()
        activity.startActivity(intent)

        // Close the app to let the installer take over
        activity.finishAndRemoveTask()
        System.exit(0)
    }

    private fun greet(name: String) {
        binding.tvName.text = name
    }

    private fun pickCount(user: Map<String, Any?>): Int {
        val bal = user["balanceFields"]
        if (bal != null) {
            val n = pickNum(bal)
            if (n != null) return maxOf(0, n)
        }
        val sec = user["balanceSeconds"]?.let { pickNum(it) } ?: 0
        return if (sec > 0) maxOf(1, sec / 60) else 0
    }

    private fun pickNum(v: Any?): Int? = when (v) {
        is PyObject -> try { v.toFloat().toInt() } catch (_: Exception) { null }
        is Number -> v.toInt()
        else -> v?.toString()?.trim()?.toFloatOrNull()?.toInt()
    }

    private fun credit(txt: String, warn: Boolean) {
        binding.tvCredit.text = "Tín dụng: $txt"
        binding.tvCredit.setTextColor(
            ContextCompat.getColor(
                requireContext(),
                if (warn) R.color.error else R.color.onSecondaryContainer
            )
        )
    }

    private fun server(text: String, ok: Boolean) {
        binding.tvServer.text = text
        binding.tvServer.setTextColor(
            ContextCompat.getColor(
                requireContext(),
                if (ok) R.color.primary else R.color.onSurfaceVariant
            )
        )
    }

    private fun gate(msg: String?) {
        if (msg.isNullOrEmpty()) {
            binding.tvGate.visibility = View.GONE
        } else {
            binding.tvGate.text = msg
            binding.tvGate.visibility = View.VISIBLE
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}