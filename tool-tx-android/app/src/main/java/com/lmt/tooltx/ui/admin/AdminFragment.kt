package com.lmt.tooltx.ui.admin

import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.chaquo.python.PyObject
import com.google.android.material.card.MaterialCardView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentAdminBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class AdminFragment : Fragment() {

    private var _binding: FragmentAdminBinding? = null
    private val binding get() = _binding!!

    private var users: Map<String, Any?> = emptyMap()
    private var query: String = ""
    private var rate: Int = 5000

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
        binding.cardAddUser.setOnClickListener { showCreateUserDialog() }
        binding.btnAddUser.setOnClickListener { showCreateUserDialog() }
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
            val r = bridge.getRate()
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                users = us
                rate = r
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
                gravity = Gravity.CENTER
                setPadding(dp(4), dp(14), dp(4), dp(14))
            }
            b.layoutUserList.addView(empty)
        } else {
            for ((uid, user) in filtered) {
                b.layoutUserList.addView(buildUserRow(uid, user))
            }
        }
    }

    // ── Danh sách user dạng thanh ngang bo tròn ────────────────
    private fun buildUserRow(uid: String, user: PyObject): View {
        val activity = requireActivity()
        val username = user.str("username").ifEmpty { "?" }
        val display = user.str("displayName").ifEmpty { "" }
        val picks = user.balance()
        val hasPicks = picks > 0

        val row = MaterialCardView(activity).apply {
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = dp(8) }
            radius = dp(22).toFloat()
            cardElevation = 0f
            strokeWidth = 0
            setCardBackgroundColor(ContextCompat.getColor(activity, R.color.surfaceContainerHigh))
            isClickable = true
            isFocusable = true
            foreground = ctxRipple(activity)
        }

        val inner = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        row.addView(inner)

        val initial = username.take(1).uppercase(Locale.ROOT)
        val avatar = TextView(activity).apply {
            text = initial
            textSize = 16f
            setTypeface(typeface, Typeface.BOLD)
            gravity = Gravity.CENTER
            setTextColor(ContextCompat.getColor(activity, R.color.primary))
            background = rounded(activity, dp(22).toFloat(), R.color.primaryContainer)
            layoutParams = LinearLayout.LayoutParams(dp(44), dp(44))
        }
        inner.addView(avatar)

        val nameBox = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(12)
            }
        }
        val name = TextView(activity).apply {
            text = username
            setTextColor(ContextCompat.getColor(activity, R.color.onSurface))
            textSize = 15f
            setTypeface(typeface, Typeface.BOLD)
        }
        val sub = TextView(activity).apply {
            text = if (display.isNotEmpty()) display else ""
            setTextColor(ContextCompat.getColor(activity, R.color.onSurfaceVariant))
            textSize = 12f
        }
        nameBox.addView(name)
        if (display.isNotEmpty()) nameBox.addView(sub)
        inner.addView(nameBox)

        val picksChip = chip(
            activity,
            text = if (hasPicks) picks.toString() else "HẾT LƯỢT",
            textColor = ContextCompat.getColor(activity, if (hasPicks) R.color.green else R.color.red),
            bgColor = ContextCompat.getColor(
                activity,
                if (hasPicks) R.color.greenContainer else R.color.errorContainer
            )
        )
        inner.addView(picksChip)

        row.setOnClickListener { showUserDialog(uid, user) }
        return row
    }

    // ── Popup chi tiết user ────────────────────────────────────
    private fun showUserDialog(uid: String, user: PyObject) {
        val username = user.str("username").ifEmpty { "?" }
        val display = user.str("displayName").ifEmpty { "" }
        val role = user.str("role").ifEmpty { "user" }
        val picks = user.balance()
        val created = fmtTime(user.str("createdAt").toLongOrNull() ?: 0L)
        val last = fmtTime(user.str("lastSeen").toLongOrNull() ?: 0L)

        val msg = buildString {
            append(if (display.isNotEmpty()) "Tên: $display\n" else "")
            append("Quyền: ${role.uppercase()}\n")
            append("Lượt đoán: $picks\n")
            append("Mã tài khoản: $uid\n")
            if (created.isNotEmpty()) append("Tạo lúc: $created\n")
            if (last.isNotEmpty()) append("Hoạt động: $last")
        }

        MaterialAlertDialogBuilder(requireContext())
            .setTitle(if (display.isNotEmpty()) "$username ($display)" else username)
            .setMessage(msg)
            .setNeutralButton("Cộng trừ lượt") { _, _ -> showBalanceDialog(uid, username, picks) }
            .setPositiveButton("Đổi quyền") { _, _ ->
                confirmRole(uid, username, if (role == "admin") "user" else "admin")
            }
            .setNegativeButton("Xóa") { _, _ -> confirmDelete(uid, username) }
            .show()
    }

    private fun showBalanceDialog(uid: String, username: String, current: Int) {
        val activity = requireActivity()
        val box = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(4), dp(24), dp(0))
        }
        val info = TextView(activity).apply {
            text = "Hiện tại: $current lượt  •  Mỗi lượt = ${fmtMoney(rate)} VNĐ"
            setTextColor(ContextCompat.getColor(activity, R.color.onSurfaceVariant))
            textSize = 13f
            setPadding(dp(2), dp(0), dp(2), dp(12))
        }
        box.addView(info)
        val input = EditText(activity).apply {
            hint = "vd: 10 (thêm) hoặc -5 (trừ)"
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED
            setTextColor(ContextCompat.getColor(activity, R.color.onSurface))
            setHintTextColor(ContextCompat.getColor(activity, R.color.onSurfaceVariant))
            setTextSize(16f)
        }
        box.addView(input)

        MaterialAlertDialogBuilder(activity)
            .setTitle("Cộng / trừ lượt - $username")
            .setView(box)
            .setPositiveButton("Áp dụng") { _, _ ->
                val delta = input.text?.toString()?.trim()?.toIntOrNull()
                val b = _binding ?: return@setPositiveButton
                if (delta == null || delta == 0) {
                    b.tvAdminSub.text = "Nhập số lượt cần thêm/trừ"
                    showBalanceDialog(uid, username, current)
                } else {
                    applyBalance(uid, maxOf(0, current + delta))
                }
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    // ── Popup tạo user / admin ─────────────────────────────────
    private fun showCreateUserDialog() {
        val activity = requireActivity()
        val box = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(4), dp(24), dp(0))
        }

        val userField = field(activity, "Username (3-20 ký tự)", InputType.TYPE_CLASS_TEXT)
        val passField = field(activity, "Mật khẩu (>= 6 ký tự)", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        val picksField = field(activity, "Số lượt đoán cấp", InputType.TYPE_CLASS_NUMBER)
        picksField.setText("10")
        box.addView(userField)
        box.addView(passField)
        box.addView(picksField)

        val roleGroup = RadioGroup(activity).apply {
            orientation = RadioGroup.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { topMargin = dp(8) }
        }
        val rbUser = RadioButton(activity).apply {
            text = "USER"
            isChecked = true
        }
        val rbAdmin = RadioButton(activity).apply {
            text = "ADMIN"
        }
        roleGroup.addView(rbUser)
        roleGroup.addView(rbAdmin)
        box.addView(roleGroup)

        MaterialAlertDialogBuilder(activity)
            .setTitle("Tạo tài khoản mới")
            .setView(box)
            .setPositiveButton("Tạo") { _, _ ->
                val username = userField.text?.toString()?.trim()?.lowercase() ?: ""
                val password = passField.text?.toString() ?: ""
                val rawPicks = picksField.text?.toString()?.trim() ?: ""
                val b = _binding ?: return@setPositiveButton
                if (username.length < 3 || password.length < 6) {
                    b.tvAdminSub.text = "Username >= 3 ký tự, mật khẩu >= 6 ký tự"
                } else {
                    val picks = rawPicks.toIntOrNull() ?: 0
                    val role = if (roleGroup.checkedRadioButtonId == rbAdmin.id) "admin" else "user"
                    createUser(username, password, picks, role)
                }
            }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun createUser(username: String, password: String, picks: Int, role: String) {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            var ok = true
            var err = ""
            try {
                bridge.addUser(username, password, picks, role)
            } catch (e: Exception) {
                ok = false
                err = e.message ?: ""
            }
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.tvAdminSub.text =
                    if (ok) "Đã tạo $username + $picks lượt (${role.uppercase()})"
                    else "Tạo $username thất bại: $err"
                loadData()
            }
        }
    }

    // ── Hành động tốc độ ───────────────────────────────────────
    private fun saveRate() {
        val raw = (binding.etRate.text?.toString() ?: "").trim()
        val r = raw.toIntOrNull()
        if (r == null || r < 1) {
            binding.tvAdminSub.text = "Giá phải là số >= 1"
            return
        }
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.setRate(r)
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.tvAdminSub.text = "Đã lưu giá ${fmtMoney(r)} VNĐ / lượt"
                loadData()
            }
        }
    }

    private fun applyBalance(uid: String, balance: Int) {
        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            bridge.updateBalance(uid, balance)
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.tvAdminSub.text = "Đã cập nhật lượt cho user."
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

    // ── Tiện ích UI ────────────────────────────────────────────
    private fun field(activity: androidx.fragment.app.FragmentActivity, hint: String, inputType: Int): TextInputEditText {
        val input = TextInputEditText(activity).apply {
            this.hint = hint
            this.inputType = inputType
            setTextColor(ContextCompat.getColor(activity, R.color.onSurface))
            setHintTextColor(ContextCompat.getColor(activity, R.color.onSurfaceVariant))
            setTextSize(16f)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = dp(12) }
        }
        return input
    }

    private fun chip(activity: androidx.fragment.app.FragmentActivity, text: String, textColor: Int, bgColor: Int): TextView {
        return TextView(activity).apply {
            this.text = text
            setTextColor(textColor)
            textSize = 12f
            setTypeface(typeface, Typeface.BOLD)
            gravity = Gravity.CENTER
            background = rounded(activity, dp(14).toFloat(), bgColor)
            setPadding(dp(12), dp(6), dp(12), dp(6))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { marginStart = dp(8) }
        }
    }

    private fun rounded(activity: androidx.fragment.app.FragmentActivity, radius: Float, colorRes: Int): GradientDrawable {
        return GradientDrawable().apply {
            cornerRadius = radius
            setColor(ContextCompat.getColor(activity, colorRes))
        }
    }

    private fun ctxRipple(activity: androidx.fragment.app.FragmentActivity): android.graphics.drawable.RippleDrawable {
        val shape = GradientDrawable().apply {
            cornerRadius = dp(22).toFloat()
            setColor(ContextCompat.getColor(activity, R.color.surfaceContainerHigh))
        }
        return android.graphics.drawable.RippleDrawable(
            android.content.res.ColorStateList.valueOf(
                ContextCompat.getColor(activity, R.color.primaryContainer)
            ),
            shape,
            null
        )
    }

    private fun fmtMoney(v: Int): String {
        val s = String.format(Locale.ROOT, "%,d", v).replace(",", ".")
        return s
    }

    private fun fmtTime(ms: Long): String {
        if (ms <= 0) return ""
        return try {
            SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()).format(Date(ms))
        } catch (_: Exception) {
            ""
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