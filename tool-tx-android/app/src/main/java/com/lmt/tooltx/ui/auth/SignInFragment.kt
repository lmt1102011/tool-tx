package com.lmt.tooltx.ui.auth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentSigninBinding
import com.lmt.tooltx.ui.home.HomeFragment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SignInFragment : Fragment() {

    private var _binding: FragmentSigninBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSigninBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.tvStatus.visibility = View.GONE
        binding.etUsername.setText("")
        binding.etPassword.setText("")

        binding.btnSubmit.setOnClickListener { doSignIn() }
        binding.btnSwitch.setOnClickListener {
            (requireActivity() as MainActivity).showFragment(SignUpFragment::class.java, "signup")
        }
    }

    private fun doSignIn() {
        val username = (binding.etUsername.text?.toString() ?: "").trim()
        val password = binding.etPassword.text?.toString() ?: ""
        if (username.isEmpty() || password.isEmpty()) {
            setStatus("Nhập tên đăng nhập và mật khẩu.", true)
            return
        }

        binding.btnSubmit.isEnabled = false
        setStatus("Đang đăng nhập...", false)

        GlobalScope.launch(Dispatchers.IO) {
            val bridge: PythonBridge = (requireActivity() as MainActivity).getBridge()
            val result = bridge.login(username, password)
            withContext(Dispatchers.Main) {
                val b = _binding ?: return@withContext
                b.btnSubmit.isEnabled = true
                val ok = result["ok"] == true
                if (ok) {
                    (requireActivity() as MainActivity)
                        .showFragment(HomeFragment::class.java, "home")
                } else {
                    setStatus(result["error"]?.toString() ?: "Đăng nhập thất bại.", true)
                }
            }
        }
    }

    private fun setStatus(msg: String, isError: Boolean) {
        binding.tvStatus.text = msg
        binding.tvStatus.visibility = View.VISIBLE
        binding.tvStatus.setTextColor(
            ContextCompat.getColor(
                requireContext(),
                if (isError) R.color.error else R.color.onSurfaceVariant
            )
        )
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}