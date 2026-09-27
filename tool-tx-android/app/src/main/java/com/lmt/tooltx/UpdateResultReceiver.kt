package com.lmt.tooltx

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.widget.Toast

/**
 * Nhận kết quả cài APK từ PackageInstaller.
 *
 * Trước đây updater chỉ startActivity(ACTION_INSTALL_PACKAGE) rồi im lặng,
 * nên khi Android từ chối file app không hề biết: không báo lỗi, vẫn ghi
 * KEY_PENDING, và lần mở sau thông tin bị pendingUpdateDone() xóa mất.
 * Bộ nhận này lưu cả trường hợp thành công lẫn thất bại vào prefs để hiện
 * lại sau khi app khởi động lại.
 */
class UpdateResultReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val prefs = context.getSharedPreferences(AppUpdater.PREFS_KEY, Context.MODE_PRIVATE)
        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, Int.MIN_VALUE)
        val message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)

        if (status == PackageInstaller.STATUS_SUCCESS) {
            prefs.edit()
                .putString(AppUpdater.KEY_RESULT, "OK")
                .putString(AppUpdater.KEY_RESULT_DETAIL, AppUpdater.versionName(context))
                .remove(AppUpdater.KEY_PENDING_KEY)
                .apply()
        } else {
            // Giữ KEY_PENDING: nếu phiên bản thực sự không đổi thì app vẫn
            // biết mình đang ở giữa một lần cập nhật chưa thành công.
            prefs.edit()
                .putString(AppUpdater.KEY_RESULT, "FAIL")
                .putString(
                    AppUpdater.KEY_RESULT_DETAIL,
                    "${statusName(status)}${if (message.isNullOrBlank()) "" else ": $message"}"
                )
                .apply()
        }
        val msg = if (status == PackageInstaller.STATUS_SUCCESS) {
            "Da cap nhat xong ${AppUpdater.versionName(context)}"
        } else {
            "Cap nhat that bai - ${prefs.getString(AppUpdater.KEY_RESULT_DETAIL, "")}"
        }
        Toast.makeText(context, msg, Toast.LENGTH_LONG).show()
    }

    private fun statusName(status: Int): String = when (status) {
        PackageInstaller.STATUS_FAILURE_BLOCKED -> "bi chan boi chinh sach"
        PackageInstaller.STATUS_FAILURE_ABORTED -> "da huy"
        PackageInstaller.STATUS_FAILURE_INVALID -> "APK khong hop le"
        PackageInstaller.STATUS_FAILURE_CONFLICT -> "xung dot phien ban"
        PackageInstaller.STATUS_FAILURE_STORAGE -> "khong du bo nho"
        PackageInstaller.STATUS_FAILURE_TIMEOUT -> "het thoi gian"
        PackageInstaller.STATUS_FAILURE_INCOMPATIBLE -> "khong tuong thich phien ban"
        else -> "ma loi $status"
    }

    companion object {
        fun pendingIntent(context: Context, reqCode: Int): PendingIntent {
            val i = Intent(context, UpdateResultReceiver::class.java)
            val flags = PendingIntent.FLAG_UPDATE_CURRENT
            return if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                // Phải MUTABLE vì PackageInstaller ghi kết quả vào intent này.
                PendingIntent.getBroadcast(context, reqCode, i, flags or PendingIntent.FLAG_MUTABLE)
            } else {
                PendingIntent.getBroadcast(context, reqCode, i, flags)
            }
        }
    }
}
