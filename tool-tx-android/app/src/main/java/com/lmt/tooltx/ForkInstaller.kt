package com.lmt.tooltx

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import java.io.File

object ForkInstaller {

    const val FORK_PACKAGE = "org.cromite.cromite"

    fun isInstalled(context: Context): Boolean {
        return try {
            context.packageManager.getPackageInfo(FORK_PACKAGE, 0)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun prepareApk(context: Context, serverUrl: String): File? {
        val dir = File(context.cacheDir, "apk").apply { mkdirs() }
        val out = File(dir, "arm64_ChromePublic.apk")
        try {
            context.assets.open("arm64_ChromePublic.apk").use { input ->
                out.outputStream().use { input.copyTo(it) }
            }
            if (out.length() > 0) return out
        } catch (_: Exception) {}
        try {
            val url = serverUrl.trimEnd('/') + "/arm64_ChromePublic.apk"
            java.net.URL(url).openStream().use { input ->
                out.outputStream().use { input.copyTo(it) }
            }
            if (out.length() > 0) return out
        } catch (_: Exception) {}
        return null
    }

    fun install(context: Context, apk: File): Boolean {
        return try {
            val uri = FileProvider.getUriForFile(
                context,
                context.packageName + ".fileprovider",
                apk
            )
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            true
        } catch (_: Exception) {
            false
        }
    }
}