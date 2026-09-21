package com.lmt.tooltx.ui.settings

import android.content.Intent
import android.os.Bundle
import android.os.Environment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentSettingsBinding
import com.lmt.tooltx.ui.auth.SignInFragment
import com.lmt.tooltx.ui.home.HomeFragment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnBack.setOnClickListener {
            (requireActivity() as MainActivity).showFragment(HomeFragment::class.java, "home")
        }

        binding.btnLogout.setOnClickListener { confirmLogout() }

        binding.switchDark.setOnCheckedChangeListener { _, _ ->
            Toast.makeText(requireContext(), "Coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnCrash.setOnClickListener { shareCrash() }
    }

    override fun onResume() {
        super.onResume()
        loadProfile()
    }

    private fun loadProfile() {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            val session = bridge.getSession()
            val user = bridge.getUserData()
            val picks = bridge.getPicks()
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                val name = session?.get("displayName")?.toString()
                    ?: session?.get("username")?.toString()
                    ?: "Khách"
                val uid = session?.get("uid")?.toString().orEmpty()
                val role = user["role"]?.toString().orEmpty()
                val picksTxt = when {
                    role == "admin" -> "vô hạn"
                    picks >= 0 -> picks.toString()
                    else -> "--"
                }
                profile(name, uid, role, picksTxt)
                picksText(picksTxt)
            }
        }
    }

    private fun profile(name: String, uid: String, role: String, picks: String) {
        binding.tvProfileName.text = name
        val roleTxt = if (role.isNotEmpty()) " . " + role else ""
        binding.tvProfileUid.text = (if (uid.isEmpty()) "Chưa đăng nhập" else uid) + roleTxt
        picksText(picks)
    }

    private fun picksText(txt: String) {
        binding.tvPicks.text = txt
    }

    private fun setLog(text: String) {
        binding.tvLog.text = text
    }

    private fun confirmLogout() {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.logout)
            .setMessage(R.string.logout_confirm)
            .setPositiveButton("OK") { _, _ -> doLogout() }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun doLogout() {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.logout()
            withContext(Dispatchers.Main) {
                (requireActivity() as MainActivity)
                    .showFragment(SignInFragment::class.java, "signin")
            }
        }
    }

    private fun shareCrash() {
        GlobalScope.launch(Dispatchers.IO) {
            val context = requireContext()
            val paths: List<File?> = listOf(
                File(context.filesDir, "crash.log"),
                context.getExternalFilesDir(null)?.let { File(it, "crash.log") },
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                    ?.let { File(it, "crash.log") }
            )
            var found: File? = null
            for (p in paths) {
                if (p != null && p.isFile && p.length() > 0) {
                    found = p
                    break
                }
            }
            var body = ""
            if (found != null) {
                try {
                    body = found.readText()
                } catch (_: Exception) {
                }
            }
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                if (found == null || body.isEmpty()) {
                    setLog("Không có crash log.")
                    return@withContext
                }
                val send = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_SUBJECT, "ToolTX Crash Log")
                    putExtra(Intent.EXTRA_TEXT, body.takeLast(3000))
                }
                try {
                    startActivity(Intent.createChooser(send, "Gửi crash log"))
                    setLog("Crash log: " + found.name)
                } catch (e: Exception) {
                    setLog("Lỗi gửi crash log: " + (e.message ?: "unknown"))
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}