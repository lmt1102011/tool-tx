package com.lmt.tooltx.ui.topup

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.lmt.tooltx.MainActivity
import com.lmt.tooltx.R
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.databinding.FragmentTopupBinding
import com.lmt.tooltx.ui.home.HomeFragment

class TopUpFragment : Fragment() {

    private var _binding: FragmentTopupBinding? = null
    private val binding get() = _binding!!

    private val banks = listOf("Vietcombank", "MB Bank", "Techcombank", "BIDV", "VPBank")
    private val topUpUrl = "https://lmt1102011.github.io/tool-tx/user.html"

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentTopupBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnBack.setOnClickListener {
            (requireActivity() as MainActivity).showFragment(HomeFragment::class.java, "home")
        }

        binding.btnOpenWeb.setOnClickListener { openWeb() }

        val rows = listOf(
            binding.rowBank0,
            binding.rowBank1,
            binding.rowBank2,
            binding.rowBank3,
            binding.rowBank4
        )
        rows.forEachIndexed { index, row ->
            row.setOnClickListener {
                if (index < banks.size) {
                    showBankDialog(banks[index])
                }
            }
        }
    }

    private fun showBankDialog(bank: String) {
        val message = getString(R.string.transfer_desc) + "\n\nNgân hàng: $bank"
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.transfer_title)
            .setMessage(message)
            .setPositiveButton(R.string.open_topup_web) { _, _ -> openWeb() }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun openWeb() {
        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(topUpUrl))
            startActivity(intent)
        } catch (e: Exception) {
            Toast.makeText(requireContext(), "Không mở được trang nạp tiền", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}