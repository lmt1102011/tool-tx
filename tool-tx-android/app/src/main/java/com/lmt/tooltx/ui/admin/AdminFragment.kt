package com.lmt.tooltx.ui.admin

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.chaquo.python.PyObject
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentAdminBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AdminFragment : Fragment() {

    private var _binding: FragmentAdminBinding? = null
    private val binding get() = _binding!!

    private var users: Map<String, Any?> = emptyMap()
    private var query: String = ""

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAdminBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnSaveRate.setOnClickListener { saveRate() }
        binding.btnCreateUser.setOnClickListener { createUser() }
        binding.etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                query = (s?.toString() ?: "").trim().lowercase()
                renderUsers()
            }
        })
    }

    override fun onResume() {
        super.onResume()
        loadData()
    }

    private fun loadData() {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            val us = bridge.listUsers()
            val rate = bridge.getRate()
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                users = us
                b.etRate.setText(rate.toString())
                renderUsers()
            }
        }
    }

    private fun renderUsers() {
        val b = _binding ?: return
        val nonAdmin = ArrayList<Pair<String, PyObject>>()
        for ((uid, value) in users) {
            if (value is PyObject) {
                val user = value as PyObject
                if (!user.str("role").equals("admin", ignoreCase = true)) {
                    nonAdmin.add(uid to user)
                }
            }
        }

        b.tvStatUsers.text = nonAdmin.size.toString()
        b.tvStatPicks.text = nonAdmin.sumOf { it.second.balance() }.toString()

        val filtered = nonAdmin
            .sortedByDescending { it.second.seen() }
            .filter { it.second.str("username").lowercase().contains(query) }

        b.layoutUserList.removeAllViews()
        if (filtered.isEmpty()) {
            val empty = TextView(requireContext()).apply {
                text = "Chưa có user nào."
                setTextColor(ContextCompat.getColor(requireContext(), R.color.onSurfaceVariant))
                textSize = 12f
                setPadding(dp(4), dp(12), dp(4), dp(12))
            }
            b.layoutUserList.addView(empty)
        } else {
            for ((uid, user) in filtered) {
                b.layoutUserList.addView(buildUserRow(uid, user))
            }
        }
    }

    private fun buildUserRow(uid: String, user: PyObject): View {
        val activity = requireActivity()

        val row = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(4), dp(8), dp(4), dp(8))
        }

        val nameBox = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        val name = TextView(activity).apply {
            text = user.str("username")
            setTextColor(ContextCompat.getColor(activity, R.color.onSurface))
            textSize = 15f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        val display = TextView(activity).apply {
            text = user.str("displayName")
            setTextColor(ContextCompat.getColor(activity, R.color.onSurfaceVariant))
            textSize = 10f
        }
        nameBox.addView(name)
        nameBox.addView(display)
        row.addView(nameBox)

        val balance = user.balance()
        val picksTxt = TextView(activity).apply {
            text = balance.toString()
            textSize = 13f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setTextColor(
                ContextCompat.getColor(
                    activity,
                    if (balance <= 0) R.color.red else R.color.green
                )
            )
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { marginStart = dp(8) }
        }
        row.addView(picksTxt)

        val targetRole = if (user.str("role").equals("admin", ignoreCase = true)) "user" else "admin"
        val btnRole = MaterialButton(activity).apply {
            text = "Quyền"
            textSize = 12f
            minimumHeight = dp(34)
            layoutParams = LinearLayout.LayoutParams(dp(56), dp(34)).apply { marginStart = dp(6) }
            setOnClickListener {
                confirmRole(uid, user.str("username"), targetRole)
            }
        }
        row.addView(btnRole)

        val btnDelete = MaterialButton(activity).apply {
            text = "Xóa"
            textSize = 12f
            minimumHeight = dp(34)
            setTextColor(ContextCompat.getColor(activity, R.color.error))
            layoutParams = LinearLayout.LayoutParams(dp(52), dp(34)).apply { marginStart = dp(6) }
            setOnClickListener {
                confirmDelete(uid, user.str("username"))
            }
        }
        row.addView(btnDelete)

        row.minimumHeight = dp(52)
        return row
    }

    private fun saveRate() {
        val raw = (binding.etRate.text?.toString() ?: "").trim()
        val rate = raw.toIntOrNull()
        if (rate == null || rate < 1) {
            binding.tvAdminSub.text = "Giá phải là số >= 1"
            return
        }
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.setRate(rate)
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.tvAdminSub.text = "Đã lưu giá $rate VNĐ / lượt"
                loadData()
            }
        }
    }

    private fun createUser() {
        val username = (binding.etNewUser.text?.toString() ?: "").trim().lowercase()
        val password = binding.etNewPass.text?.toString() ?: ""
        val rawPicks = (binding.etNewPicks.text?.toString() ?: "").trim()
        if (username.length < 3 || password.length < 6) {
            binding.tvAdminSub.text = "Username ≥ 3 ký tự, mật khẩu ≥ 6 ký tự"
            return
        }
        val picks = rawPicks.toIntOrNull() ?: 0
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.addUser(username, password, picks)
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.tvAdminSub.text = "Đã tạo $username + $picks lượt"
                b.etNewUser.text?.clear()
                b.etNewPass.text?.clear()
                b.etNewPicks.setText("10")
                loadData()
            }
        }
    }

    private fun confirmRole(uid: String, username: String, target: String) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Đổi quyền")
            .setMessage("Đổi quyền của $username thành ${target.uppercase()}?")
            .setPositiveButton("OK") { _, _ -> applyRole(uid, target) }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun applyRole(uid: String, target: String) {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.updateRole(uid, target)
            withContext(Dispatchers.Main) {
                if (_binding == null) return@withContext
                loadData()
            }
        }
    }

    private fun confirmDelete(uid: String, username: String) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Xóa user")
            .setMessage("Xóa tài khoản \"$username\"? Người này sẽ không đăng nhập được nữa.")
            .setPositiveButton("Xóa") { _, _ -> deleteUser(uid) }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun deleteUser(uid: String) {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.deleteUser(uid)
            withContext(Dispatchers.Main) {
                if (_binding == null) return@withContext
                loadData()
            }
        }
    }

    private fun PyObject.str(key: String): String =
        try {
            this.callAttr("__getitem__", key).toString()
        } catch (_: Exception) {
            ""
        }

    private fun PyObject.balance(): Int =
        str("balanceFields").toDoubleOrNull()?.toInt() ?: 0

    private fun PyObject.seen(): Long =
        str("lastSeen").toLongOrNull() ?: 0L

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}