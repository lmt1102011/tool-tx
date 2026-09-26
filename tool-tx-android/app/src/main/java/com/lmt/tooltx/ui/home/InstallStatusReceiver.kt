package com.lmt.tooltx.ui.home

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.widget.Toast

/**
 * Nhận kết quả cài đặt APK từ PackageInstaller. Receiver phải khai báo trong
 * manifest vì app có thể đã bị hệ thống dừng khi gói mới được thay thế.
 */
class InstallStatusReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, Int.MIN_VALUE)
        if (status == PackageInstaller.STATUS_SUCCESS) {
            Toast.makeText(context, "Cài đặt thành công", Toast.LENGTH_LONG).show()
        } else {
            val msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)
            val detail = msg ?: ("mã $status")
            Toast.makeText(context, "Cài đặt thất bại: $detail", Toast.LENGTH_LONG).show()
        }
    }
}
