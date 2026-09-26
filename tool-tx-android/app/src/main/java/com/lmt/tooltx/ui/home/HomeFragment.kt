package com.lmt.tooltx.ui.home

import android.app.DownloadManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.IntentSender
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.database.Cursor
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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
            requireContext().packageManager.getPackageInfo(requireContext().packageName, 0).versionName ?: "0.0.0"
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
        val dm = requireContext().getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val request = DownloadManager.Request(Uri.parse(downloadUrl))
            .setTitle("tool-tx cập nhật")
            .setDescription("Đang tải phiên bản mới...")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalFilesDir(requireContext(), Environment.DIRECTORY_DOWNLOADS, "tool-tx-update.apk")
            .setAllowedOverMetered(true)
            .setAllowedOverRoaming(false)
            .setRequiresCharging(false)
            .setAllowedNetworkTypes(DownloadManager.Request.NETWORK_WIFI or DownloadManager.Request.NETWORK_MOBILE)

        val downloadId = dm.enqueue(request)
        b.btnUpdate.isEnabled = false
        b.btnUpdate.text = "ĐANG TẢI..."

        // Poll download progress - track max bytes to avoid negative progress
        GlobalScope.launch(Dispatchers.Main) {
            var maxBytes = 0L
            var lastProgress = -1
            while (true) {
                delay(800)
                val query = DownloadManager.Query().setFilterById(downloadId)
                val cursor = dm.query(query)
                if (cursor.moveToFirst()) {
                    val status = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
                    val bytesDownloaded = cursor.getLong(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR))
                    val totalSize = cursor.getLong(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES))
                    
                    // Track max bytes seen (monotonic)
                    if (bytesDownloaded > maxBytes) maxBytes = bytesDownloaded
                    
                    if (totalSize > 0 && maxBytes > 0) {
                        val progress = (maxBytes * 100 / totalSize).toInt().coerceAtMost(100)
                        if (progress != lastProgress) {
                            b.btnUpdate.text = "ĐANG TẢI $progress%"
                            lastProgress = progress
                        }
                    } else if (maxBytes > 0) {
                        // Total size unknown yet, show bytes
                        val mb = maxBytes / (1024 * 1024)
                        b.btnUpdate.text = "ĐANG TẢI ${mb}MB"
                    }
                    
                    if (status == DownloadManager.STATUS_SUCCESSFUL) {
                        cursor.close()
                        val localUri = dm.getUriForDownloadedFile(downloadId)
                        installApkWithPackageInstaller(localUri)
                        break
                    } else if (status == DownloadManager.STATUS_FAILED) {
                        cursor.close()
                        val reason = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_REASON))
                        b.btnUpdate.isEnabled = true
                        b.btnUpdate.text = "CẬP NHẬT"
                        Toast.makeText(requireContext(), "Tải thất bại (mã: $reason)", Toast.LENGTH_LONG).show()
                        break
                    }
                }
                cursor.close()
            }
        }
    }

    private fun installApkWithPackageInstaller(apkUri: Uri?) {
        if (apkUri == null) {
            Toast.makeText(requireContext(), "Không tìm thấy file APK", Toast.LENGTH_SHORT).show()
            resetUpdateButton()
            return
        }
        
        try {
            val pm = requireContext().packageManager
            val installer = pm.packageInstaller
            val sessionParams = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
            sessionParams.setAppPackageName(requireContext().packageName)
            
            val sessionId = installer.createSession(sessionParams)
            val session = installer.openSession(sessionId)
            
            val inputStream = requireContext().contentResolver.openInputStream(apkUri)
            val outputStream = session.openWrite("tool-tx-update.apk", 0, -1)
            
            inputStream?.use { src ->
                outputStream.use { dest ->
                    src.copyTo(dest)
                }
            }
            
            session.fsync(outputStream)
            session.commit(createInstallIntent())
            
            // App will be installed, finish current app
            requireActivity().finishAndRemoveTask()
            System.exit(0)
        } catch (e: Exception) {
            // Fallback to intent method
            installApkFallback(apkUri)
        }
    }

    private fun createInstallIntent(): IntentSender {
        val intent = Intent(requireContext(), MainActivity::class.java)
        intent.action = Intent.ACTION_VIEW
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return PendingIntent.getActivity(
            requireContext(), 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        ).intentSender
    }

    private fun installApkFallback(apkUri: Uri) {
        val intent = Intent(Intent.ACTION_VIEW)
        intent.setDataAndType(apkUri, "application/vnd.android.package-archive")
        intent.flags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK
        try {
            requireActivity().startActivity(intent)
            requireActivity().finishAndRemoveTask()
            System.exit(0)
        } catch (e: Exception) {
            Toast.makeText(requireContext(), "Cài đặt thất bại: ${e.message}", Toast.LENGTH_LONG).show()
            resetUpdateButton()
        }
    }

    private fun resetUpdateButton() {
        val b = _binding ?: return
        b.btnUpdate.isEnabled = true
        b.btnUpdate.text = "CẬP NHẬT"
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